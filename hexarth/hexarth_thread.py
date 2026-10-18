import logging
import time
import threading
from hexarth.hexarth_state import HexarthState
from hexarth.hex_bot import HexBot

UPDATE_HTZ = 1
UPDATE_INTERVAL = 1.0 / UPDATE_HTZ

# How long shutting down waits for the robot to be told to stop
STOP_TIMEOUT_SECONDS = 2.0

_stop_requested = threading.Event()
_hexarth_thread = None

def start_thread(hexarth_state: HexarthState, stationary_mode: bool = False):
    """
    Create a thread that is responsible for controlling hexarth.
    """
    global _hexarth_thread
    _hexarth_thread = threading.Thread(target=loop, args=(hexarth_state, stationary_mode), name="hexarth")
    _hexarth_thread.start()


def stop():
    """
    End the hexarth thread, which stops the robot on its way out. Waits for that, but not forever.
    """
    _stop_requested.set()
    if _hexarth_thread:
        _hexarth_thread.join(STOP_TIMEOUT_SECONDS)
        if _hexarth_thread.is_alive():
            logging.warning("Hexarth thread did not stop within %.0fs, the robot may still be moving "
                            "until the ESP32's 3 second heartbeat runs out", STOP_TIMEOUT_SECONDS)


def loop(hexarth_state: HexarthState, stationary_mode: bool = False):
    logging.info("Starting hexarth thread, stationary mode %s", "on" if stationary_mode else "off")

    try:
        hexbot = HexBot(hexarth_state, stationary_mode)
    except Exception:
        logging.exception("Could not open the serial port to the robot, it will not move")
        return

    while not _stop_requested.is_set():
        update_start_time = time.perf_counter()
        hexbot.update()

        # Only the time the update itself took comes off the wait, so updates stay one interval apart
        update_seconds = time.perf_counter() - update_start_time
        _stop_requested.wait(max(0, UPDATE_INTERVAL - update_seconds))

    hexbot.shut_down()
    logging.info("Hexarth thread stopped")