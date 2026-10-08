import logging
import threading

class HeadState:
    def __init__(self):
        self._lock = threading.Lock()
        self.queued_moves = []

    def queue_move(self, pan: float, tilt: float, speed: float):
        """
        Queue a head movement.

        :param pan: The angle to turn to in degrees, 0 is straight ahead and positive is to the right.
        :param tilt: The angle to tilt to in degrees. The scale is inverted, 0 is level and negative is up.
        :param speed: How fast to get there, in degrees per second.
        """
        with self._lock:
            self.queued_moves.append({"pan": pan, "tilt": tilt, "speed": speed})
            logging.info("Queued head move to pan %s, tilt %s at %s degrees a second, %d now waiting",
                         pan, tilt, speed, len(self.queued_moves))

    def pop_move(self):
        """Get and remove the first queued move"""
        with self._lock:
            if len(self.queued_moves) > 0:
                return self.queued_moves.pop(0)
            return None

    def clear_moves(self):
        """Clear all queued moves"""
        with self._lock:
            self.queued_moves = []
