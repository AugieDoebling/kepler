"""Shows the display frames on a web page, for testing without the real display.

    from display.simulator import DisplaySimulator

    simulator = DisplaySimulator()
    simulator.start()            # then open http://localhost:8080
    simulator.show(frame_image)  # call for every frame

The page is a single image that the browser keeps replacing as frames arrive
(motion JPEG), so it needs nothing installed and no JavaScript. It is only
reachable from this machine.
"""
import io
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from PIL import Image

HOST = "localhost"
PORT = 8080

# How much larger than the real display the frame is drawn on the page
PAGE_SCALE = 2
JPEG_QUALITY = 90

# Lets a stream notice that its viewer has gone, even if no new frames are arriving
FRAME_WAIT_SECONDS = 1.0

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Kepler display</title>
<style>
  body {{ margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #1b1b1b; }}
  img {{ width: {width}px; height: {height}px; border-radius: 12px; outline: 2px solid #3a3a3a; background: black; }}
</style>
</head>
<body><img src="/stream" alt="Kepler display"></body>
</html>
"""


class DisplaySimulator:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self._condition = threading.Condition()
        self._frame: Optional[Image.Image] = None
        self._frame_number = 0
        self._viewers = 0
        self._server: Optional[ThreadingHTTPServer] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self):
        """
        Start serving the page. Raises OSError if the port is already in use.
        """
        simulator = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    simulator._send_page(self)
                elif self.path == "/stream":
                    simulator._send_stream(self)
                else:
                    self.send_error(404)

            def log_message(self, format, *args):
                logging.debug("Display simulator: " + format, *args)

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as e:
            raise OSError(f"Could not start the display simulator on {self.url}: {e}") from e

        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, name="display-simulator", daemon=True).start()
        logging.info("Display simulator running at %s", self.url)

    def show(self, image: Image.Image):
        """
        Make this frame the one on the page.
        """
        with self._condition:
            self._frame = image
            self._frame_number += 1
            self._condition.notify_all()

    def _send_page(self, handler: BaseHTTPRequestHandler):
        with self._condition:
            size = self._frame.size if self._frame else (240, 284)
        body = PAGE.format(width=size[0] * PAGE_SCALE, height=size[1] * PAGE_SCALE).encode("utf-8")

        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def _send_stream(self, handler: BaseHTTPRequestHandler):
        handler.send_response(200)
        handler.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()

        sent_frame_number = 0
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._frame_number != sent_frame_number, FRAME_WAIT_SECONDS)
                    if self._frame is None:
                        continue
                    frame, sent_frame_number = self._frame, self._frame_number

                # Encoded outside the lock so a slow viewer never holds up the display thread
                jpeg = io.BytesIO()
                frame.save(jpeg, format="JPEG", quality=JPEG_QUALITY)
                data = jpeg.getvalue()

                handler.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                handler.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii"))
                handler.wfile.write(data)
                handler.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            # The browser tab was closed
            pass


def start_simulator(config: dict) -> Optional[DisplaySimulator]:
    """
    Start the display simulator if it is enabled in the config.

    Returns the simulator to show frames on, or None when it is off.
    """
    if not config.get("display_simulator", False):
        return None

    simulator = DisplaySimulator()
    simulator.start()
    print(f"Display simulator is on, open {simulator.url}")
    return simulator
