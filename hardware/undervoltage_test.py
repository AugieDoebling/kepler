"""Watch for undervoltage without running the whole robot, printing what the hardware thread would log.

Works from the repo root or from inside hardware/. Stop with Ctrl-C:

    python undervoltage_test.py                # check every 3 seconds
    python undervoltage_test.py --interval 1   # check every second
"""
import argparse
import logging
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Replace this script's own folder on the path, it holds nothing that should be imported by bare name
sys.path[0] = REPO_ROOT

from hardware.hardware_thread import UndervoltageCheck


def main():
    parser = argparse.ArgumentParser(description="Watch for undervoltage and print what is found.")
    parser.add_argument("--interval", type=float, default=3.0, help="seconds between checks (default: 3)")
    args = parser.parse_args()

    # The same format the robot's log file uses
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s")

    # Reports what has happened since the Pi started
    check = UndervoltageCheck()
    print(f"Checking every {args.interval:g}s, only problems are printed. Stop with Ctrl-C.")

    try:
        while True:
            time.sleep(args.interval)
            check.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
