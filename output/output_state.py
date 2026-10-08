import threading
from typing import Optional
from display.display_state import DisplayState

class OutputState:
    def __init__(self):
        self._lock = threading.Lock()
        self.output_queue = []
        self._unfinished = 0

    def queue_output(self, text: str):
        with self._lock:
            self.output_queue.append(text)
            self._unfinished += 1
    
    def pop_output(self):
        with self._lock:
            if len(self.output_queue) > 0:
                return self.output_queue.pop(0)
            return None

    def has_queued_output(self):
        return len(self.output_queue) > 0

    def finish_output(self):
        """
        Called by the output thread once a popped item has been spoken, skipped, or has failed.
        """
        with self._lock:
            self._unfinished -= 1

    def is_speaking(self):
        """
        True from the moment text is queued until the last of it has finished playing.
        """
        with self._lock:
            return self._unfinished > 0


def start_output(config: dict, display_state: Optional[DisplayState] = None) -> Optional[OutputState]:
    """
    Start speech output if it is enabled in the config.

    Returns the state to queue text on, or None when audio output is off.
    """
    if not config.get("audio_output", False):
        return None

    # Imported here so that the speech dependencies are only needed when audio output is on
    from output import output_thread
    from output.speech import SpeechSynthesizer

    output_state = OutputState()
    output_thread.start_thread(output_state, SpeechSynthesizer.from_config(config), display_state)
    return output_state
