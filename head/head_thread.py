import logging
import threading
from head.head_state import HeadState
from head.pan_tilt import PanTiltHat

# How often to look for a new move while the head is still
IDLE_POLL_SECONDS = 0.1

# Fast enough to be quick about it, slow enough not to jerk the head
SHUTDOWN_CENTER_SPEED = 90.0
# Long enough to center from the far end of the head's travel at that speed
STOP_TIMEOUT_SECONDS = 3.0

_stop_requested = threading.Event()
_head_thread = None

def start_thread(head_state: HeadState, stationary_mode: bool = False):
    """
    Create a thread that is responsible for moving the head.
    """
    global _head_thread
    _head_thread = threading.Thread(target=loop, args=(head_state, stationary_mode), name="head")
    _head_thread.start()


def stop():
    """
    End the head thread, which centers and relaxes the head on its way out. Waits for that, but not forever.
    """
    _stop_requested.set()
    if _head_thread:
        _head_thread.join(STOP_TIMEOUT_SECONDS)
        if _head_thread.is_alive():
            logging.warning("Head thread did not stop within %.0fs, the head may not be centered", STOP_TIMEOUT_SECONDS)


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

    while not _stop_requested.is_set():
        move = head_state.pop_move()
        if move is None:
            _stop_requested.wait(IDLE_POLL_SECONDS)
            continue

        logging.info("Moving head to pan %s, tilt %s at %s degrees a second", move["pan"], move["tilt"], move["speed"])
        try:
            if head:
                # Blocks until the head has arrived
                head.look_smooth(pan=move["pan"], tilt=move["tilt"], speed=move["speed"], stop_event=_stop_requested)
                pan, tilt = head.pan, head.tilt
            else:
                # Moves still take their full time, the command just never reaches the servos
                travel = max(abs(move["pan"] - pan), abs(move["tilt"] - tilt))
                logging.info("Stationary mode, simulating a head move of %.0f degrees", travel)
                _stop_requested.wait(travel / move["speed"])
                pan, tilt = move["pan"], move["tilt"]
        except Exception:
            # One failed move should not stop the head for good
            logging.exception("Head move failed: %s", move)

    if head:
        try:
            head.center(smooth=True, speed=SHUTDOWN_CENTER_SPEED)
        finally:
            # Left powered, a loaded servo buzzes and heats up while nothing is driving it
            head.close()
    logging.info("Head thread stopped")
