"""Shows the display frames on the real screen, a Waveshare 1.83" ST7789 LCD on SPI0.

    from display.screen import start_screen

    screen = start_screen()      # None if the screen could not be set up
    screen.show(frame_image)     # call for every frame

The screen's VCC must be on 3.3V. On 5V the backlight lights but the panel shows nothing,
and since SPI only sends, nothing here can tell.
"""
import logging
import threading
from typing import Optional
from PIL import Image

WIDTH = 240
HEIGHT = 284
X_OFFSET = 0
Y_OFFSET = 36

# The panel is fine at much higher speeds, Waveshare's own example runs it at 40MHz
BAUDRATE = 16_000_000


class Screen:
    """Sends frames to the screen from its own thread, as a full frame takes longer to send than to draw."""

    def __init__(self):
        # Imported here so the rest of Kepler still runs on a machine without the Pi's pins
        import board
        import busio
        import digitalio
        from adafruit_rgb_display import st7789

        spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        # Resets the panel as part of setting it up
        self._display = st7789.ST7789(
            spi,
            cs=digitalio.DigitalInOut(board.D5),
            dc=digitalio.DigitalInOut(board.D24),
            rst=digitalio.DigitalInOut(board.D26),
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
