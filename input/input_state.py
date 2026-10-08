import logging
import threading
from typing import Optional
from display.display_state import DisplayState
from output.output_state import OutputState

class InputState:
    def __init__(self):
        self._condition = threading.Condition()
        self.input_queue = []

    def queue_message(self, text: str):
        if not text.strip():
            return
        with self._condition:
            self.input_queue.append(text.strip())
            self._condition.notify()

    def wait_for_message(self) -> str:
        """
        Block until the user has said or typed something, and return it.

        Everything queued is returned as one message, so a sentence that was split by a pause,
        or something said while the LLM was busy, is a single user turn.
        """
        with self._condition:
            while not self.input_queue:
                self._condition.wait()
            message = " ".join(self.input_queue)
            self.input_queue.clear()
            return message


def start_input(config: dict, output_state: Optional[OutputState] = None,
                display_state: Optional[DisplayState] = None) -> Optional[InputState]:
    """
    Start speech input if it is enabled in the config.

    Returns the state to take user messages from, or None when audio input is off.
    """
    if not config.get("audio_input", False):
        return None
    logging.info("Starting speech input")

    # Imported here so that the listening dependencies are only needed when audio input is on
    from input import input_thread
    from input.recognizer import SpeechRecognizer
    from input.wake_word import WakeWordFilter

    recognizer = SpeechRecognizer.from_config(config)
    print(f"Loading the '{recognizer.model}' listening model...")
    recognizer.load()

    input_state = InputState()
    input_thread.start_threads(input_state, recognizer, WakeWordFilter.from_config(config), output_state,
                               display_state)
    return input_state
