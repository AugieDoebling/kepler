import logging
import time
import threading
from hexarth.hexarth_state import HexarthState
from hexarth.hex_bot import HexBot

UPDATE_HTZ = 1
UPDATE_INTERVAL = 1.0 / UPDATE_HTZ

def start_thread(hexarth_state: HexarthState, stationary_mode: bool = False):
    """
    Create a thread that is responsible for controlling hexarth.
    """
    hexarth_thread = threading.Thread(target=loop, args=(hexarth_state, stationary_mode), name="hexarth")
    hexarth_thread.start()


def loop(hexarth_state: HexarthState, stationary_mode: bool = False):
    logging.info("Starting hexarth thread, stationary mode %s", "on" if stationary_mode else "off")

    try:
        hexbot = HexBot(hexarth_state, stationary_mode)
    except Exception:
        logging.exception("Could not open the serial port to the robot, it will not move")
        return

    while True:
        update_start_time = time.perf_counter()
        hexbot.update()

        # Only the time the update itself took comes off the wait, so updates stay one interval apart
        update_seconds = time.perf_counter() - update_start_time
        time.sleep(max(0, UPDATE_INTERVAL - update_seconds))