import logging
import threading
from enum import Enum

class EyeState(Enum):
    """What the robot is doing, shown as the color of the eye."""
    REGULAR = "regular"
    SPEAKING = "speaking"
    BOOTING = "booting"
    ERROR = "error"

class DisplayState:
    def __init__(self):
        self.is_loading = False
        self.at_attention = False
        self.eye_state = EyeState.BOOTING
        self._lock = threading.Lock()

    def set_attention(self, attention: bool):
        with self._lock:
            if attention != self.at_attention:
                logging.debug("Display attention %s", "on" if attention else "off")
            self.at_attention = attention
        
    def set_loading(self, loading: bool):
        with self._lock:
            if loading != self.is_loading:
                logging.debug("Display loading %s", "on" if loading else "off")
            self.is_loading = loading

    def set_eye_state(self, eye_state: EyeState):
        with self._lock:
            if eye_state != self.eye_state:
                logging.debug("Display eye state %s -> %s", self.eye_state.value, eye_state.value)
            self.eye_state = eye_state
        
    