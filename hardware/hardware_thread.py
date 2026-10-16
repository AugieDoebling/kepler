import glob
import logging
import subprocess
import threading
import time

CHECK_INTERVAL_SECONDS = 10

# The hwmon device that watches the Pi's 5V supply. Its hwmonN number is not fixed between boots.
UNDERVOLTAGE_HWMON_NAME = "rpi_volt"
# What the kernel logs each time the 5V supply drops below its limit
UNDERVOLTAGE_MESSAGE = "Undervoltage detected"
JOURNAL_CURSOR_PREFIX = "-- cursor: "

def start_thread():
    """
    Create a thread that watches for hardware problems and logs them.
    """
    hardware_thread = threading.Thread(target=loop, name="hardware")
    hardware_thread.start()


def loop():
    logging.info("Starting hardware thread, checking every %ss", CHECK_INTERVAL_SECONDS)

    checks = [UndervoltageCheck()]

    while True:
        check_start_time = time.perf_counter()
        for check in checks:
            try:
                check.run()
            except Exception:
                # One broken check should not stop the others
                logging.exception("Hardware check %s failed", type(check).__name__)

        # Only the time the checks took comes off the wait, so checks stay one interval apart
        check_seconds = time.perf_counter() - check_start_time
        time.sleep(max(0, CHECK_INTERVAL_SECONDS - check_seconds))


class UndervoltageCheck:
    """
    Logs every time the Pi's 5V supply has dropped too low since the last check.

    The dips often last only a couple of seconds, so reading the alarm every 10 seconds would miss most of them.
    The kernel logs each one, so those log entries are what get counted, and the alarm only says whether the
    supply is still low right now.
    """

    def __init__(self):
        # Where in the kernel log the last check got to. None when the kernel log can not be read.
        self.journal_cursor = None

        events, cursor = self.read_kernel_log(["--boot"])
        if cursor is None:
            logging.warning("Can not read the kernel log, undervoltage will only be seen while it is happening")
            return

        self.journal_cursor = cursor
        if events:
            logging.warning("Undervoltage was detected %d times since the Pi started, last at %s",
                            len(events), events[-1])
        else:
            logging.info("No undervoltage detected since the Pi started")

    def run(self):
        undervoltage_now = self.read_alarm()

        if self.journal_cursor is None:
            if undervoltage_now:
                logging.warning("Undervoltage detected, the Pi's 5V supply is too low right now")
            return

        events, cursor = self.read_kernel_log([f"--after-cursor={self.journal_cursor}"])
        if cursor is not None:
            self.journal_cursor = cursor

        if events:
            logging.warning("Undervoltage detected %d times since the last check, at %s. %s",
                            len(events), ", ".join(events),
                            "Still too low now." if undervoltage_now else "Back to normal now.")
        elif undervoltage_now:
            # Already low at the last check and has not recovered since
            logging.warning("Undervoltage still detected, the Pi's 5V supply is too low right now")

    @staticmethod
    def read_alarm() -> bool:
        """Whether the 5V supply is below its limit right now"""
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(f"{hwmon}/name") as f:
                    if f.read().strip() != UNDERVOLTAGE_HWMON_NAME:
                        continue
                with open(f"{hwmon}/in0_lcrit_alarm") as f:
                    return f.read().strip() == "1"
            except OSError:
                continue
        return False

    @staticmethod
    def read_kernel_log(position_args: list) -> tuple:
        """
        Find the undervoltage messages in the kernel log from the given position onwards.
        Returns the time of each message and the cursor to carry on from, or no cursor when the log can not be read.
        """
        try:
            result = subprocess.run(
                ["journalctl", "--dmesg", "--quiet", "--no-pager", "--output=short-iso-precise", "--show-cursor",
                 f"--grep={UNDERVOLTAGE_MESSAGE}", *position_args],
                capture_output=True, text=True, timeout=CHECK_INTERVAL_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return [], None

        events, cursor = [], None
        for line in result.stdout.splitlines():
            if line.startswith(JOURNAL_CURSOR_PREFIX):
                cursor = line[len(JOURNAL_CURSOR_PREFIX):]
            elif UNDERVOLTAGE_MESSAGE in line:
                # The line starts with the time, e.g. 2026-10-07T22:52:57.991043-07:00
                events.append(line.split()[0].split("T")[-1][:8])
        return events, cursor
