"""Drive the pan-tilt head by hand, one command per line, without running the whole robot.

Works from the repo root or from inside head/. Angles are signed degrees from
center: pan is positive to the right, tilt is positive up.

    python pan_tilt_test.py                 # start at center, then read commands
    python pan_tilt_test.py --no-limits     # allow the full +/-90 in place of the driver's soft limits
    python pan_tilt_test.py --invert-tilt   # flip an axis that runs backwards

Commands:

    pan -10        set the pan servo to -10 degrees
    tilt 45        set the tilt servo to 45 degrees
    smooth pan 30 tilt -10 speed 45
                   glide there with look_smooth, both axes arriving together.
                   Give either axis or both; speed is degrees/sec (default 60)
    center         both axes back to 0
    relax          cut the pulses so the servos go slack
    pos            print the last commanded position
    help           show this list
    quit           relax the servos and exit (Ctrl-D and Ctrl-C do the same)
"""
import argparse
import os
import sys
import time

try:  # arrow-key history and line editing at the prompt
    import readline  # noqa: F401
except ImportError:
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Replace this script's own folder on the path, it holds nothing that should be imported by bare name
sys.path[0] = REPO_ROOT

from head.pan_tilt import PAN_CHANNEL, PAN_LIMITS, TILT_CHANNEL, TILT_LIMITS, PanTiltHat

FULL_RANGE = (-90.0, 90.0)

COMMANDS_HELP = __doc__.split("Commands:\n", 1)[1].rstrip()


def set_axis(head: PanTiltHat, axis: str, argument: str) -> None:
    try:
        angle = float(argument)
    except ValueError:
        print(f"'{argument}' is not an angle, try: {axis} 20")
        return

    head.look(**{axis: angle})

    actual = getattr(head, axis)
    if actual != angle:
        print(f"{axis} -> {actual:g} (asked for {angle:g}, clamped to the limit)")
    else:
        print(f"{axis} -> {actual:g}")


def glide(head: PanTiltHat, arguments: list[str]) -> None:
    usage = "usage: smooth [pan <degrees>] [tilt <degrees>] [speed <degrees/sec>]"

    if not arguments or len(arguments) % 2:
        print(usage)
        return

    targets = {}
    for name, value in zip(arguments[::2], arguments[1::2]):
        name = name.lower()
        if name not in ("pan", "tilt", "speed") or name in targets:
            print(usage)
            return
        try:
            targets[name] = float(value)
        except ValueError:
            print(f"'{value}' is not a number for {name}")
            return

    if "pan" not in targets and "tilt" not in targets:
        print(usage)
        return
    if targets.get("speed", 1.0) <= 0:
        print("speed has to be above 0")
        return

    started = time.monotonic()
    head.look_smooth(**targets)
    elapsed = time.monotonic() - started

    reached = []
    for axis in ("pan", "tilt"):
        if axis in targets:
            actual = getattr(head, axis)
            clamped = "" if actual == targets[axis] else f" (asked for {targets[axis]:g}, clamped to the limit)"
            reached.append(f"{axis} -> {actual:g}{clamped}")
    print(f"{', '.join(reached)} in {elapsed:.2f}s")


def run_command(head: PanTiltHat, line: str) -> bool:
    """Carry out one line of input. Returns False when it is time to exit."""
    words = line.replace("=", " ").split()
    if not words:
        return True

    command, arguments = words[0].lower(), words[1:]

    if command in ("pan", "tilt"):
        if len(arguments) != 1:
            print(f"usage: {command} <degrees>")
        else:
            set_axis(head, command, arguments[0])
    elif command == "smooth":
        glide(head, arguments)
    elif command == "center":
        head.center()
        print("pan -> 0, tilt -> 0")
    elif command == "relax":
        head.relax()
        print("servos relaxed, the next pan or tilt re-engages them")
    elif command == "pos":
        print(f"pan {head.pan:g}, tilt {head.tilt:g}")
    elif command in ("help", "?"):
        print(COMMANDS_HELP)
    elif command in ("quit", "exit", "q"):
        return False
    else:
        print(f"unknown command '{command}', try: pan <degrees>, tilt <degrees>, smooth, center, relax, pos, quit")

    return True


def main():
    parser = argparse.ArgumentParser(description="Drive the pan-tilt head by hand from stdin.")
    parser.add_argument("--no-limits", action="store_true",
                        help="allow the full +/-90 servo range in place of the driver's soft limits")
    parser.add_argument("--pan-channel", type=int, default=PAN_CHANNEL, help="PCA9685 channel of the pan servo")
    parser.add_argument("--tilt-channel", type=int, default=TILT_CHANNEL, help="PCA9685 channel of the tilt servo")
    parser.add_argument("--invert-pan", action="store_true", help="flip the pan axis")
    parser.add_argument("--invert-tilt", action="store_true", help="flip the tilt axis")
    args = parser.parse_args()

    pan_limits = FULL_RANGE if args.no_limits else PAN_LIMITS
    tilt_limits = FULL_RANGE if args.no_limits else TILT_LIMITS

    interactive = sys.stdin.isatty()

    try:
        head = PanTiltHat(
            pan_channel=args.pan_channel,
            tilt_channel=args.tilt_channel,
            pan_limits=pan_limits,
            tilt_limits=tilt_limits,
            invert_pan=args.invert_pan,
            invert_tilt=args.invert_tilt,
        )
    except (OSError, RuntimeError) as e:
        sys.exit(f"Could not reach the pan-tilt HAT: {e}")

    with head:
        print(f"Head centered. pan {pan_limits[0]:g}..{pan_limits[1]:g} (channel {args.pan_channel}), "
              f"tilt {tilt_limits[0]:g}..{tilt_limits[1]:g} (channel {args.tilt_channel}).")
        if not args.no_limits:
            print("Those are the driver's soft limits, run with --no-limits for the full +/-90.")
        if interactive:
            print("Type 'help' for the commands, 'quit' to exit.")

        try:
            while True:
                try:
                    line = input("> " if interactive else "")
                except EOFError:
                    if interactive:
                        print()  # Ctrl-D leaves the cursor on the prompt line
                    break
                if not run_command(head, line):
                    break
        except KeyboardInterrupt:
            print()
        except OSError as e:
            print(f"Lost the pan-tilt HAT: {e}")

    print("relaxed")


if __name__ == "__main__":
    main()
