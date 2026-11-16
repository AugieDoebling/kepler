import logging
import threading
from typing import Optional
from display.display_state import DisplayState
from output.output_state import OutputState

class InputState:
    def __init__(self, prompt: Optional[str] = None):
        self._condition = threading.Condition()
        self.input_queue = []
        # Printed when the robot starts waiting for the user, for typed input only
        self.prompt = prompt
        self._last_was_typed = False

    def queue_message(self, text: str, typed: bool = False):
        if not text.strip():
            return
        with self._condition:
            self.input_queue.append(text.strip())
            self._last_was_typed = typed
            self._condition.notify()

    def wait_for_message(self) -> str:
        """
        Block until the user has said or typed something, and return it.

        Everything queued is returned as one message, so a sentence that was split by a pause,
        or something said while the LLM was busy, is a single user turn.
        """
        with self._condition:
            # Only when nothing is waiting already, something typed while the robot was busy is answered straight away
            prompted = bool(self.prompt) and not self.input_queue
            if prompted:
                print(self.prompt, end="", flush=True)
            while not self.input_queue:
                self._condition.wait()
            if prompted and not self._last_was_typed:
                # Something else, like a timer, started the turn, so the reply mustn't follow the prompt on its line
                print()
            message = " ".join(self.input_queue)
            self.input_queue.clear()
            return message


def start_keyboard_input() -> InputState:
    """
    Typed input only, for when speech input is off. Messages go through an input state either way, so things
    other than the user, like timers going off, can start a turn too.
    """
    input_state = InputState(prompt="--> ")

    def keyboard_loop():
        while True:
            try:
                # No prompt here, wait_for_message shows it once the robot has finished replying
                typed = input()
            except EOFError:
                logging.info("Keyboard input closed")
                return
            input_state.queue_message(typed, typed=True)

    threading.Thread(target=keyboard_loop, name="input-keyboard", daemon=True).start()
    return input_state


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
