from output_state import OutputState
import logging
import time
import threading


def start_thread(output_state: OutputState):
    """
    Create a thread that is responsible for controlling speech and listening.
    """
    output_thread = threading.Thread(target=loop, args=(output_state))
    output_thread.start()


def loop(output_state: OutputState):
    logging.info("Starting output thread")

    while True:
        time.sleep(0.2)
        if not output_state.has_queued_output():
            continue
        
        
        
        