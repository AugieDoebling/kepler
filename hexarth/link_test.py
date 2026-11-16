"""Check the serial link to the HexArth's ESP32 without running the whole robot. Nothing here moves the legs.

Works from the repo root or from inside hexarth/:

    python link_test.py                   # 20 state queries, then a verdict on the wiring
    python link_test.py --count 200       # a longer run, to catch a link that only drops out now and then
    python link_test.py --no-oled         # leave the small screen on the robot alone
    python link_test.py --move            # then also move the legs, to check the ESP32 can drive them

Each query is {"T":130}, which only reads the robot's state. While the test runs, line 3 of the robot's
screen shows "Link test" -- if that appears but no replies come back, the Pi's TX wire works and the
problem is on the way back (the Pi's RX wire, pin 10).

--move asks before it does anything, then puts the robot in its starting pose and sways its body for a few
seconds. The feet stay where they are, so it will not walk off the table. Whether the legs moved is for you
to judge by watching -- the robot does not report its real servo positions.
"""
import argparse
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Replace this script's own folder on the path, it holds nothing that should be imported by bare name
sys.path[0] = REPO_ROOT

from hexarth import commands
from hexarth.hex_bot import SERIAL_BAUD, SERIAL_PORT

STATE_QUERY = {"T": 130}
STATE_REPLY_TYPE = 1001
# The line of the robot's screen that the startup screen leaves empty
OLED_TEST_LINE = 3

# The --move check. Sway sizes are percentages of the most the firmware allows.
POSE_SETTLE_SECONDS = 2.0
SWAY_SECONDS = 4.0
SWAY_ROLL = 40
SWAY_PITCH = 40
SWAY_FREQUENCY = 50
# How often to ask for the robot's state while it moves
MOVE_QUERY_SECONDS = 0.5


def send(port, command: dict):
    port.write((json.dumps(command) + "\n").encode())
    port.flush()


class StateReader:
    """Sends state queries and sorts out what comes back."""

    def __init__(self, port):
        self.port = port
        self.buffer = b""
        self.garbage = []
        self.last_state = None

    def query(self, wait_seconds: float) -> bool:
        """Ask for the robot's state once and wait for it. Returns whether a reply came back."""
        send(self.port, STATE_QUERY)
        answered = False
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            self.buffer += self.port.read(4096)
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                reply = json.loads(line)
            except ValueError:
                self.garbage.append(line)
                continue
            if isinstance(reply, dict) and reply.get("T") == STATE_REPLY_TYPE:
                answered = True
                self.last_state = reply
        return answered


def check_serial_setup(port_name: str):
    """Warn about the things on the Pi that are known to break this link, before blaming the wires."""
    device = os.path.basename(port_name)

    try:
        with open("/sys/class/tty/console/active") as f:
            consoles = f.read().split()
    except OSError:
        consoles = []
    try:
        with open("/proc/sys/kernel/printk") as f:
            console_level = int(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        console_level = 8
    # Undervoltage warnings are KERN_CRIT (2), which only reach the console when its level is above 2
    if device in consoles and console_level <= 2:
        print(f"Note: the kernel console is on {device}, but its level is {console_level} so warnings are held back")
        print("      until the next reboot (sudo dmesg -n 1). The lasting fix is removing console=serial0,115200")
        print("      from /boot/firmware/current/cmdline.txt.")
    elif device in consoles:
        print(f"WARNING: the kernel console is on {device}. Kernel messages (like undervoltage warnings) are sent")
        print("         to the robot, which reads them as an emergency stop: limp for 10s, deaf to commands.")
        print("         Until reboot: sudo dmesg -n 1. For good: remove console=serial0,115200 from")
        print("         /boot/firmware/current/cmdline.txt and reboot.")

    getty = subprocess.run(["systemctl", "is-active", f"serial-getty@{device}.service"],
                           capture_output=True, text=True).stdout.strip()
    if getty == "active":
        print(f"WARNING: a login console is running on {device} and will eat the robot's replies.")
        print(f"         sudo systemctl mask --now serial-getty@{device}.service")


def undervoltage_since(start_time: float) -> int:
    """How many undervoltage warnings the kernel logged since start_time, or -1 if the log can not be read."""
    try:
        result = subprocess.run(
            ["journalctl", "--dmesg", "--quiet", "--no-pager", f"--since=@{int(start_time)}",
             "--grep=Undervoltage detected"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1
    return len([line for line in result.stdout.splitlines() if "Undervoltage detected" in line])


def main():
    parser = argparse.ArgumentParser(description="Check the serial link to the HexArth's ESP32.")
    parser.add_argument("--count", type=int, default=20, help="how many state queries to send (default: 20)")
    parser.add_argument("--interval", type=float, default=0.25,
                        help="seconds to wait for each reply before sending the next query (default: 0.25)")
    parser.add_argument("--port", default=SERIAL_PORT, help=f"serial port (default: {SERIAL_PORT})")
    parser.add_argument("--move", action="store_true",
                        help="after the link check, move the legs (asks first) to check the ESP32 can drive them")
    parser.add_argument("--no-oled", action="store_true", help="do not write to the robot's screen")
    args = parser.parse_args()

    import serial

    check_serial_setup(args.port)

    try:
        port = serial.Serial(args.port, SERIAL_BAUD, timeout=0.01, write_timeout=1.0)
    except serial.SerialException as e:
        sys.exit(f"Could not open {args.port}: {e}\n(Is this user in the dialout group? Is main.py already running?)")

    start_time = time.time()
    replies = 0
    timeline = ""
    reader = StateReader(port)

    with port:
        port.reset_input_buffer()
        # A newline first, so anything half-received by the ESP32 is finished off and thrown away
        port.write(b"\n")
        # Otherwise the ESP32 echoes each command back as text
        send(port, commands.set_debug_print(False))
        if not args.no_oled:
            send(port, commands.write_oled_text(OLED_TEST_LINE, "Link test", centered=True))
        time.sleep(0.2)
        port.reset_input_buffer()

        print(f"Sending {args.count} state queries on {args.port} at {SERIAL_BAUD} baud...")
        for _ in range(args.count):
            answered = reader.query(args.interval)
            replies += answered
            timeline += "#" if answered else "."
            print(f"\r{timeline}", end="", flush=True)
        print()

        if not args.no_oled:
            send(port, commands.write_oled_text(OLED_TEST_LINE, ""))

    print(f"\nReplies: {replies}/{args.count}")
    if reader.last_state is not None:
        print(f"Robot battery/supply: {reader.last_state.get('v', 0) / 100:.2f} V")
    garbage = reader.garbage
    if garbage:
        print(f"Unreadable lines: {len(garbage)}, e.g. {garbage[0][:60]!r}")

    undervoltage = undervoltage_since(start_time)
    if undervoltage > 0:
        print(f"The Pi logged {undervoltage} undervoltage warnings during the test.")

    print()
    if replies == args.count and not garbage:
        print("Link is good.")
    elif replies == 0:
        print("No replies at all. Check, in order: the robot is switched on; the ground wire (pin 6) is connected;")
        print("pin 8 goes to pin 8 and pin 10 to pin 10 (straight through, not crossed).")
        if not args.no_oled:
            print("If 'Link test' showed on the robot's screen, Pi -> robot works and the fault is pin 10 (robot -> Pi).")
    elif garbage:
        print("Replies are arriving corrupted. Usually a loose or missing ground wire, or a wrong baud rate.")
    else:
        print("Some replies were lost.", end=" ")
        if undervoltage > 0:
            print("The undervoltage warnings above, sent to the robot by the kernel console, are the likely cause.")
        else:
            print("Look for a loose wire (wiggle them during a --count 200 run), then the warnings at the top.")

    if args.move:
        if replies == 0:
            print("\nSkipping --move, there is no point while the robot is not answering.")
        else:
            move_check(serial, args.port)


def move_check(serial, port_name: str):
    """
    Move the legs while still asking for the robot's state, so an emergency stop shows up as the replies going
    quiet: the ESP32 sits in a 10 second delay with the servos limp and answers nothing.
    """
    print("\nMove check: the robot will go to its starting pose, then sway its body for "
          f"{SWAY_SECONDS:g}s with its feet in place.")
    try:
        input("Make sure the legs are clear, then press Enter to start (Ctrl-C to skip)... ")
    except (KeyboardInterrupt, EOFError):
        print("\nSkipped.")
        return

    start_time = time.time()
    lost = 0

    with serial.Serial(port_name, SERIAL_BAUD, timeout=0.01, write_timeout=1.0) as port:
        reader = StateReader(port)
        try:
            print("Starting pose")
            send(port, commands.go_to_initial_position())
            for _ in range(int(POSE_SETTLE_SECONDS / MOVE_QUERY_SECONDS)):
                lost += not reader.query(MOVE_QUERY_SECONDS)

            print("Swaying")
            sway = commands.pose_angle_rotation(SWAY_ROLL, SWAY_PITCH, 0, SWAY_FREQUENCY)
            sway_end = time.monotonic() + SWAY_SECONDS
            while time.monotonic() < sway_end:
                # Re-sent each time round, the ESP32 drops a sway after 3 seconds without one
                send(port, sway)
                lost += not reader.query(MOVE_QUERY_SECONDS)
        finally:
            # Even on Ctrl-C, so the robot is not left swaying until its own 3 second timeout
            send(port, commands.pose_angle_rotation(0, 0, 0, 0))
            send(port, commands.stop())

        print("Stopped")

    undervoltage = undervoltage_since(start_time)
    print()
    if lost:
        print(f"The robot stopped answering {lost} times while moving.", end=" ")
        if undervoltage > 0:
            print(f"The Pi logged {undervoltage} undervoltage warnings, which the kernel console passes on to the")
            print("robot as an emergency stop. See the warning at the top about the kernel console.")
        else:
            print("Possibly an emergency stop (legs going limp) or the supply dipping under the servos' load.")
    else:
        print("The robot answered throughout, so nothing interrupted it.")
    print("Did the legs move? Into the starting pose, then the body tilting side to side and front to back.")
    print("  yes -> the Pi can drive the legs.")
    print("  no  -> the link is fine but the ESP32 is not driving the servos: check the servo cables and the")
    print("         robot's power switch, and listen for the servos humming under load.")


if __name__ == "__main__":
    main()
