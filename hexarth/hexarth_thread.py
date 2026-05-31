import logging
import time
import threading
from hexarth_state import HexarthState
from hex_bot import HexBot

UPDATE_HTZ = 1
UPDATE_INTERVAL = 1.0 / UPDATE_HTZ

def start_thread(hexarth_state: HexarthState):
    """
    Create a thread that is responsible for controlling hexarth.
    """
    hexarth_thread = threading.Thread(target=loop, args=(hexarth_state,))
    hexarth_thread.start()


def loop(hexarth_state: HexarthState):
    logging.info("Starting hexarth thread")

    last_update_time = time.perf_counter()
    hexbot = HexBot(hexarth_state)

    while True:
        hexbot.update()

        current_time = time.perf_counter()
        sleep_time = max(0, UPDATE_INTERVAL - (current_time - last_update_time))
        last_update_time = current_time

        time.sleep(sleep_time)