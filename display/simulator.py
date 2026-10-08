"""Shows the display frames on a web page, for testing without the real display.

    from display.simulator import DisplaySimulator

    simulator = DisplaySimulator()
    simulator.start()            # then open http://localhost:8080
    simulator.show(frame_image)  # call for every frame

The page is a single image that the browser keeps replacing as frames arrive
(motion JPEG), so it needs nothing installed and no JavaScript. It is only
reachable from this machine.

It can also be run on its own, so the page stays up while the robot is
stopped and started:

    python display/simulator.py

When the robot starts with the simulator on and finds one already running, it
sends its frames there in place of serving the page itself.
"""
import http.client
import io
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from PIL import Image

HOST = "localhost"
PORT = 8080

# How much larger than the real display the frame is drawn on the page
PAGE_SCALE = 2
DEFAULT_FRAME_SIZE = (240, 284)
JPEG_QUALITY = 90

# Lets a stream notice that its viewer has gone, even if no new frames are arriving
FRAME_WAIT_SECONDS = 1.0

# What a running simulator answers on /ping, so the robot can tell it from another program on the port
PING_REPLY = b"kepler-display-simulator"
MAX_FRAME_BYTES = 5_000_000
REMOTE_TIMEOUT_SECONDS = 2.0
REMOTE_RETRY_SECONDS = 1.0

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


def encode_frame(image: Image.Image) -> bytes:
    jpeg = io.BytesIO()
    image.save(jpeg, format="JPEG", quality=JPEG_QUALITY)
    return jpeg.getvalue()


class DisplaySimulator:
    """Serves the page, and shows on it the frames it is given."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self._condition = threading.Condition()
        self._frame: Optional[bytes] = None
        self._frame_number = 0
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
            # Lets the robot send every frame down one connection
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                if self.path == "/":
                    simulator._send_page(self)
                elif self.path == "/stream":
                    simulator._send_stream(self)
                elif self.path == "/ping":
                    simulator._send_body(self, "text/plain", PING_REPLY)
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == "/frame":
                    simulator._receive_frame(self)
                else:
                    self.send_error(404)

            def log_message(self, format, *args):
                logging.debug("Display simulator: " + format, *args)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, name="display-simulator", daemon=True).start()
        logging.info("Display simulator running at %s", self.url)

    def show(self, image: Image.Image):
        """
        Make this frame the one on the page.
        """
        self._show_jpeg(encode_frame(image))

    def _show_jpeg(self, jpeg: bytes):
        with self._condition:
            self._frame = jpeg
            self._frame_number += 1
            self._condition.notify_all()

    def _send_body(self, handler: BaseHTTPRequestHandler, content_type: str, body: bytes):
        handler.send_response(200)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def _send_page(self, handler: BaseHTTPRequestHandler):
        with self._condition:
            frame = self._frame
        size = Image.open(io.BytesIO(frame)).size if frame else DEFAULT_FRAME_SIZE
        page = PAGE.format(width=size[0] * PAGE_SCALE, height=size[1] * PAGE_SCALE)
        self._send_body(handler, "text/html; charset=utf-8", page.encode("utf-8"))

    def _send_stream(self, handler: BaseHTTPRequestHandler):
        handler.send_response(200)
        handler.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        handler.send_header("Cache-Control", "no-store")
        # The stream has no end, so the connection cannot be reused for anything after it
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.close_connection = True

        logging.info("Display simulator: a browser started watching")
        sent_frame_number = 0
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._frame_number != sent_frame_number, FRAME_WAIT_SECONDS)
                    if self._frame is None:
                        continue
                    frame, sent_frame_number = self._frame, self._frame_number

                # Written outside the lock so a slow viewer never holds up the display thread
                handler.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                handler.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                handler.wfile.write(frame)
                handler.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            # The browser tab was closed
            logging.info("Display simulator: a browser stopped watching")

    def _receive_frame(self, handler: BaseHTTPRequestHandler):
        length = int(handler.headers.get("Content-Length", 0))
        if not 0 < length <= MAX_FRAME_BYTES:
            handler.send_error(400)
            return
        self._show_jpeg(handler.rfile.read(length))
        self._send_body(handler, "text/plain", b"ok")


class RemoteDisplaySimulator:
    """Sends frames to a simulator that is running on its own, in place of serving the page from here."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self._condition = threading.Condition()
        self._frame: Optional[Image.Image] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_running(self) -> bool:
        """
        True if a display simulator, and not some other program, is answering on the port.
        """
        try:
            connection = http.client.HTTPConnection(self.host, self.port, timeout=REMOTE_TIMEOUT_SECONDS)
            connection.request("GET", "/ping")
            reply = connection.getresponse().read()
            connection.close()
            return reply == PING_REPLY
        except (OSError, http.client.HTTPException):
            return False

    def start(self):
        threading.Thread(target=self._send_loop, name="display-simulator-sender", daemon=True).start()
        logging.info("Sending display frames to the simulator at %s", self.url)

    def show(self, image: Image.Image):
        """
        Make this frame the one on the page. Returns at once, the frame is sent from another thread.
        """
        with self._condition:
            self._frame = image
            self._condition.notify()

    def _send_loop(self):
        connection = None
        connected = True
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._frame is not None)
                # Only the newest frame is kept, so falling behind drops frames and does not build a backlog
                frame, self._frame = self._frame, None

            try:
                if connection is None:
                    connection = http.client.HTTPConnection(self.host, self.port, timeout=REMOTE_TIMEOUT_SECONDS)
                connection.request("POST", "/frame", body=encode_frame(frame), headers={"Content-Type": "image/jpeg"})
                connection.getresponse().read()
                if not connected:
                    logging.info("Reconnected to the display simulator at %s", self.url)
                    connected = True
            except (OSError, http.client.HTTPException) as e:
                # The simulator was stopped. Keep trying, it may be started again.
                # Logged once per outage, not on every retry
                if connected:
                    logging.warning("Lost the display simulator at %s, retrying: %s", self.url, e)
                    connected = False
                if connection:
                    connection.close()
                connection = None
                time.sleep(REMOTE_RETRY_SECONDS)


def start_simulator(config: dict):
    """
    Start the display simulator if it is enabled in the config.

    Returns something to show frames on, or None when it is off. If a simulator is already
    running on its own, the frames are sent to it.
    """
    if not config.get("display_simulator", False):
        return None

    simulator = DisplaySimulator()
    try:
        simulator.start()
    except OSError as e:
        remote = RemoteDisplaySimulator()
        if not remote.is_running():
            raise OSError(f"Could not start the display simulator on {simulator.url}: {e}") from e
        remote.start()
        print(f"Display simulator is on, using the one already running at {remote.url}")
        return remote

    print(f"Display simulator is on, open {simulator.url}")
    return simulator


def main():
    simulator = DisplaySimulator()
    try:
        simulator.start()
    except OSError as e:
        if RemoteDisplaySimulator().is_running():
            print(f"A display simulator is already running at {simulator.url}")
        else:
            print(f"Could not start the display simulator on {simulator.url}: {e}")
        return 1

    print(f"Display simulator running, open {simulator.url}")
    print("Start Kepler with display_simulator on to see its display here. Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
