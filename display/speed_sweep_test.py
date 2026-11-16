"""Steps a screen through SPI speeds, each with its own solid color, to find how fast the wiring can go.

    python3 -m display.speed_sweep_test right        # or left, or both (left then right)
    python3 -m display.speed_sweep_test right 5      # hold each color 5 seconds (default 3)

The last color that shows cleanly is the fastest speed the wiring handles:

    1 MHz red, 2 MHz green, 4 MHz blue, 8 MHz yellow, 12 MHz cyan, 16 MHz magenta,
    24 MHz white, 32 MHz orange, 64 MHz gray, 128 MHz navy

The other screen's CS is held high throughout, so it stays off the bus.
"""
import sys
import time
import board
import busio
import digitalio
from adafruit_rgb_display import st7789
from PIL import Image

STEPS = [
    (1, "red", (255, 0, 0)),
    (2, "green", (0, 255, 0)),
    (4, "blue", (0, 0, 255)),
    (8, "yellow", (255, 255, 0)),
    (12, "cyan", (0, 255, 255)),
    (16, "magenta", (255, 0, 255)),
    (24, "white", (255, 255, 255)),
    (32, "orange", (255, 128, 0)),
    (64, "gray", (128, 128, 128)),
    (128, "navy", (0, 0, 128)),
]

# A full frame at 16 bits a pixel
FRAME_BITS = 240 * 284 * 16

# CS, DC, RST
PINS = {
    "left": (board.D5, board.D23, board.D27),
    "right": (board.D6, board.D24, board.D4),
    # left swap cs
    "test1": (board.D6, board.D23, board.D27),
    # left swap dc
    "test2": (board.D5, board.D24, board.D27),
    # left swap rst
    "test3": (board.D5, board.D23, board.D4),

}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in (*PINS, "both"):
        print(__doc__)
        print(f"Pin sets: {', '.join(PINS)}, or both (left then right)")
        return 1
    sides = ["left", "right"] if sys.argv[1] == "both" else [sys.argv[1]]
    hold_seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0

    spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    # The test pin sets reuse the real screens' pins, and each pin can only be claimed once
    claimed = {}
    def claim(pin):
        if pin.id not in claimed:
            claimed[pin.id] = digitalio.DigitalInOut(pin)
        return claimed[pin.id]
    screens = {side: [claim(pin) for pin in pins] for side, pins in PINS.items()}
    # Deselect both, so neither screen listens while the other is being tested
    for cs, _, _ in screens.values():
        cs.switch_to_output(value=True)

    for side in sides:
        cs, dc, rst = screens[side]
        print(f"\n=== {side} screen ===", flush=True)
        for mhz, name, rgb in STEPS:
            display = st7789.ST7789(
                spi, cs=cs, dc=dc, rst=rst,
                baudrate=mhz * 1_000_000, width=240, height=284, x_offset=0, y_offset=36,
            )
            image = Image.new("RGB", (240, 284), rgb)
            # The SPI hardware rounds the speed down to one it can make, so time the frame to see the real speed
            start = time.perf_counter()
            # No reset here: setting up the ST7789 already resets it, and a reset after that puts it back to sleep
            display.image(image)
            seconds = time.perf_counter() - start
            effective_mhz = FRAME_BITS / seconds / 1_000_000
            print(f"  {mhz:>3} MHz asked, {effective_mhz:5.1f} MHz effective ({1 / seconds:4.1f} fps): {name}",
                  flush=True)
            time.sleep(hold_seconds)
    print("\ndone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
