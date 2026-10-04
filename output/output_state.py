import threading
from typing import Optional

class OutputState:
    def __init__(self):
        self._lock = threading.Lock()
        self.output_queue = []

    def queue_output(self, text: str):
        with self._lock:
            self.output_queue.append(text)
    
    def pop_output(self):
        with self._lock:
            if len(self.output_queue) > 0:
                return self.output_queue.pop(0)
            return None

    def has_queued_output(self):
        return len(self.output_queue) > 0


def start_output(config: dict) -> Optional[OutputState]:
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
    output_thread.start_thread(output_state, SpeechSynthesizer.from_config(config))
    return output_state
