"""Shows the display frames on the real screens, two Waveshare 1.83" ST7789 LCDs (the eyes) on SPI0.

    from display.screen import start_screen

    screen = start_screen()      # None if the screens could not be set up
    screen.show(frame_image)     # call for every frame

Both screens always show the same frame, so they are sent it together: each has its own CS, DC and
RST pins, and those are driven in pairs so both screens listen to the one transfer. That keeps the
frame rate the same as for one screen.

Each screen's VCC must be on 3.3V. On 5V the backlight lights but the panel shows nothing,
and since SPI only sends, nothing here can tell. `python3 -m display.speed_sweep_test both`
checks each screen on its own.
"""
import logging
import threading
from typing import Optional
from PIL import Image

WIDTH = 240
HEIGHT = 284
X_OFFSET = 0
Y_OFFSET = 36

# What is asked for, the SPI hardware rounds it down: 64MHz gives about 40MHz in practice, around 36 frames a
# second, just above the display thread's 30. Both screens were clean here and failed at 128MHz, the panel's
# own limit is about 62.5MHz. If frames come out garbled, 32MHz (about 20 frames a second) has more margin.
BAUDRATE = 64_000_000


class PinPair:
    """Two pins that always move together, standing in for one pin. Only what the display library uses."""

    def __init__(self, first, second):
        self._pins = (first, second)

    def switch_to_output(self, value=False):
        for pin in self._pins:
            pin.switch_to_output(value=value)

    @property
    def value(self):
        return self._pins[0].value

    @value.setter
    def value(self, value):
        for pin in self._pins:
            pin.value = value


class Screen:
    """Sends frames to the screen from its own thread, as a full frame takes longer to send than to draw."""

    def __init__(self):
        # Imported here so the rest of Kepler still runs on a machine without the Pi's pins
        import board
        import busio
        import digitalio
        from adafruit_rgb_display import st7789

        def pins(left, right):
            return PinPair(digitalio.DigitalInOut(left), digitalio.DigitalInOut(right))

        spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        # Resets both panels as part of setting them up. Don't reset again after this, it puts them back to sleep.
        self._display = st7789.ST7789(
            spi,
            cs=pins(board.D5, board.D6),
            dc=pins(board.D23, board.D24),
            rst=pins(board.D27, board.D4),
            baudrate=BAUDRATE, width=WIDTH, height=HEIGHT, x_offset=X_OFFSET, y_offset=Y_OFFSET,
        )
        self._condition = threading.Condition()
        self._frame: Optional[Image.Image] = None
        # Held while talking to the panel, so clearing it never interleaves with a frame being sent
        self._write_lock = threading.Lock()
        self._cleared = False

    def start(self):
        threading.Thread(target=self._send_loop, name="display-screen", daemon=True).start()
        logging.info("Sending display frames to the screen at %d MHz", BAUDRATE // 1_000_000)

    def show(self, image: Image.Image):
        """
        Make this frame the one on the screen. Returns at once, the frame is sent from another thread.
        """
        with self._condition:
            self._frame = image
            self._condition.notify()

    def _send_loop(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._frame is not None)
                # Only the newest frame is kept, so falling behind drops frames and does not build a backlog
                frame, self._frame = self._frame, None
            with self._write_lock:
                # A frame picked up just before the screen was cleared must not be drawn over it
                if self._cleared:
                    return
                try:
                    self._display.image(frame)
                except Exception:
                    logging.exception("Could not send a frame to the screen")

    def clear(self):
        """
        Blank the screen and stop showing frames. Waits until the screen is blank.
        """
        with self._condition:
            self._frame = None
        with self._write_lock:
            self._cleared = True
            self._display.fill(0)
        logging.info("Screen cleared")


def start_screen():
    """
    Set up the screen and start sending frames to it. Returns None if it could not be set up.
    """
    try:
        screen = Screen()
    except Exception:
        logging.exception("Could not set up the screen, the display will not be shown")
        return None
    screen.start()
    return screen
