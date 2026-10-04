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
    hexarth_thread = threading.Thread(target=loop, args=(hexarth_state, stationary_mode))
    hexarth_thread.start()


def loop(hexarth_state: HexarthState, stationary_mode: bool = False):
    logging.info("Starting hexarth thread, stationary mode %s", "on" if stationary_mode else "off")

    last_update_time = time.perf_counter()
    try:
        hexbot = HexBot(hexarth_state, stationary_mode)
    except Exception:
        logging.exception("Could not open the serial port to the robot, it will not move")
        return

    while True:
        hexbot.update()

        current_time = time.perf_counter()
        sleep_time = max(0, UPDATE_INTERVAL - (current_time - last_update_time))
        last_update_time = current_time

        time.sleep(sleep_time)