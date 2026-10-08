import logging
import time
import threading
from head.head_state import HeadState
from head.pan_tilt import PanTiltHat

# How often to look for a new move while the head is still
IDLE_POLL_SECONDS = 0.1

def start_thread(head_state: HeadState, stationary_mode: bool = False):
    """
    Create a thread that is responsible for moving the head.
    """
    head_thread = threading.Thread(target=loop, args=(head_state, stationary_mode), name="head")
    head_thread.start()


def loop(head_state: HeadState, stationary_mode: bool = False):
    logging.info("Starting head thread, stationary mode %s", "on" if stationary_mode else "off")

    head = None
    if not stationary_mode:
        try:
            # Centers the head as it starts
            head = PanTiltHat()
        except Exception:
            logging.exception("Could not reach the pan-tilt head, it will not move")
            return

    # Where the head was last sent, used to work out how long a simulated move takes
    pan, tilt = 0.0, 0.0

    while True:
        move = head_state.pop_move()
        if move is None:
            time.sleep(IDLE_POLL_SECONDS)
            continue

        logging.info("Moving head to pan %s, tilt %s at %s degrees a second", move["pan"], move["tilt"], move["speed"])
        try:
            if head:
                # Blocks until the head has arrived
                head.look_smooth(pan=move["pan"], tilt=move["tilt"], speed=move["speed"])
                pan, tilt = head.pan, head.tilt
            else:
                # Moves still take their full time, the command just never reaches the servos
                travel = max(abs(move["pan"] - pan), abs(move["tilt"] - tilt))
                logging.info("Stationary mode, simulating a head move of %.0f degrees", travel)
                time.sleep(travel / move["speed"])
                pan, tilt = move["pan"], move["tilt"]
        except Exception:
            # One failed move should not stop the head for good
            logging.exception("Head move failed: %s", move)
