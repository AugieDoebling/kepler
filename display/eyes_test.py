"""Runs the planet eye on both real screens, the same way main does, to check them by eye.

    python3 -m display.eyes_test         # 60 seconds
    python3 -m display.eyes_test 180     # a 3 minute soak

Goes through display/screen.py and the real display thread, so it tests what main runs. Along the way:

  - the eye starts in its normal state, so the planets come out from behind the iris and orbit
  - attention switches on and off every 10 seconds
  - for 10 seconds starting at 30, the eye turns green for speaking

Watch for torn, garbled or wrongly colored frames. The frame rate is printed every 30 seconds and should
sit at about 30, the display thread's rate. Both screens are blanked at the end, also on Ctrl-C.
"""
import logging
import sys
import threading
import time
from display import display_thread
from display.display_state import DisplayState, EyeState
from display.screen import start_screen

ATTENTION_SWITCH_SECONDS = 10
SPEAKING_START_SECONDS = 30
SPEAKING_SECONDS = 10
FPS_REPORT_SECONDS = 30


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(levelname)s %(message)s")

    screen = start_screen()
    if screen is None:
        print("Could not set up the screens, see the error above")
        return 1

    # Counts the frames that actually reach the screens, not just the ones drawn
    frames_sent = 0
    send_frame = screen._display.image
    def counting_send(image):
        nonlocal frames_sent
        send_frame(image)
        frames_sent += 1
    screen._display.image = counting_send

    state = DisplayState()
    # A new state starts out booting, with the planets hidden behind the iris. main changes it after startup.
    state.set_eye_state(EyeState.REGULAR)
    threading.Thread(target=display_thread.loop, args=(state, screen), name="display", daemon=True).start()

    start = last_report = time.perf_counter()
    frames_at_last_report = 0
    try:
        for second in range(1, duration + 1):
            time.sleep(1)
            if second % ATTENTION_SWITCH_SECONDS == 0:
                at_attention = (second // ATTENTION_SWITCH_SECONDS) % 2 == 1
                state.set_attention(at_attention)
                print(f"{second:>4}s: attention {'on' if at_attention else 'off'}", flush=True)
            if second == SPEAKING_START_SECONDS:
                state.set_eye_state(EyeState.SPEAKING)
                print(f"{second:>4}s: speaking, the eye turns green", flush=True)
            if second == SPEAKING_START_SECONDS + SPEAKING_SECONDS:
                state.set_eye_state(EyeState.REGULAR)
                print(f"{second:>4}s: back to regular", flush=True)
            if second % FPS_REPORT_SECONDS == 0:
                now = time.perf_counter()
                print(f"{second:>4}s: {(frames_sent - frames_at_last_report) / (now - last_report):.1f} fps",
                      flush=True)
                last_report, frames_at_last_report = now, frames_sent
    except KeyboardInterrupt:
        print("\nStopped early")
    finally:
        total = time.perf_counter() - start
        print(f"{frames_sent} frames reached the screens in {total:.0f}s, {frames_sent / total:.1f} fps average")
        screen.clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
