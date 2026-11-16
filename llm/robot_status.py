import glob
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

# When this program started, for how long the robot has been awake
STARTED_AT = time.monotonic()


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _hwmon(name: str) -> str | None:
    """The sysfs folder of the hardware monitor with this name, such as "cpu_thermal" or "rpi_volt"."""
    for folder in glob.glob("/sys/class/hwmon/hwmon*"):
        if _read(f"{folder}/name") == name:
            return folder
    return None


def _duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    parts = [f"{days} day{'s' * (days != 1)}"] * bool(days) + [f"{hours} hour{'s' * (hours != 1)}"] * bool(hours)
    parts.append(f"{minutes} minute{'s' * (minutes != 1)}")
    return " ".join(parts)


def _cpu_temperature() -> str | None:
    millidegrees = _read("/sys/class/thermal/thermal_zone0/temp")
    if millidegrees is None:
        return None
    celsius = int(millidegrees) / 1000
    # The Pi 5 starts slowing itself down at 80°C and gets much slower at 85°C
    feeling = "cool" if celsius < 60 else "warm" if celsius < 75 else "hot, close to slowing down"
    return f"CPU temperature: {celsius:.0f}°C ({feeling})"


def _power() -> str | None:
    folder = _hwmon("rpi_volt")
    if folder is None:
        return None
    low_now = _read(f"{folder}/in0_lcrit_alarm") == "1"
    line = "Power: the supply voltage is too low right now" if low_now else "Power: the supply voltage is fine right now"
    # The legs and the Pi share a 5 V supply, so walking can pull it down
    warnings = _undervoltage_warnings_since_boot()
    if warnings:
        line += f", but it has dipped too low {warnings} time{'s' * (warnings != 1)} since the Pi started"
    return line


def _undervoltage_warnings_since_boot() -> int:
    try:
        result = subprocess.run(["journalctl", "-k", "-b", "--no-pager", "-q", "--grep=Undervoltage detected"],
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return sum("Undervoltage detected" in line for line in result.stdout.splitlines())


def _wifi() -> str | None:
    # /proc/net/wireless has a line per interface: name, status, link quality, signal level in dBm, ...
    lines = (_read("/proc/net/wireless") or "").splitlines()[2:]
    if not lines:
        return "Wi-Fi: not connected"
    fields = lines[0].split()
    try:
        signal_dbm = int(float(fields[3]))
    except (IndexError, ValueError):
        return None
    strength = "strong" if signal_dbm >= -55 else "good" if signal_dbm >= -67 else "weak" if signal_dbm >= -78 else "very weak"
    return f"Wi-Fi: {strength} signal ({signal_dbm} dBm)"


def _memory() -> str | None:
    info = {}
    for line in (_read("/proc/meminfo") or "").splitlines():
        key, _, value = line.partition(":")
        info[key] = int(value.split()[0]) if value.split() else 0
    if "MemTotal" not in info or "MemAvailable" not in info:
        return None
    used = 1 - info["MemAvailable"] / info["MemTotal"]
    return f"Memory: {used:.0%} in use of {info['MemTotal'] / 1024 / 1024:.0f} GB"


def _load() -> str | None:
    try:
        one_minute = os.getloadavg()[0]
    except OSError:
        return None
    cores = os.cpu_count() or 1
    return f"CPU load: {min(one_minute / cores, 1):.0%} busy over the last minute"


def _disk() -> str:
    usage = shutil.disk_usage("/")
    return f"Storage: {usage.free / 1024 ** 3:.0f} GB free of {usage.total / 1024 ** 3:.0f} GB"


def robot_status() -> str:
    """
    Check on your own body: temperature, power supply, Wi-Fi, memory, storage and how long you have been awake. Use it when asked how you are feeling or whether anything is wrong with you.
    """
    uptime = _read("/proc/uptime")
    lines = [f"Awake for {_duration(time.monotonic() - STARTED_AT)}"
             + (f" (the computer has been on for {_duration(float(uptime.split()[0]))})" if uptime else "")]
    for check in (_cpu_temperature, _power, _load, _memory, _disk, _wifi):
        try:
            line = check()
        except Exception:
            # One unreadable sensor shouldn't stop the others being reported
            logging.exception("robot_status check %s failed", check.__name__)
            continue
        if line:
            lines.append(line)
    return "\n".join(lines)
