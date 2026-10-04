from input.console import SpeechConsole
from input.input_state import InputState
from input.recognizer import SpeechRecognizer
from input.wake_word import WakeWordFilter
from output.output_state import OutputState
from typing import Optional
import logging
import time
import threading

# Keep ignoring the microphone for this long after the robot stops speaking, to let the room go quiet
MUTE_TAIL_SECONDS = 0.3
MUTE_POLL_SECONDS = 0.05


def start_threads(input_state: InputState, recognizer: SpeechRecognizer, wake_word: WakeWordFilter,
                  output_state: Optional[OutputState] = None):
    """
    Start listening to the microphone and the keyboard. The recognizer must already be loaded.
    """
    logging.info("Starting speech input with model %s, wake word '%s'", recognizer.model, wake_word.wake_word)

    console = SpeechConsole()

    def on_partial(text):
        # Once the wake word has been heard the line stays on screen, even if the text is revised
        if console.active or wake_word.matches(text):
            console.show(text)

    def on_line(line):
        text = wake_word.filter(line.text)
        if text is None:
            logging.debug("Heard, but not addressed to the robot: %s", line.text)
            if wake_word.matches(line.text):
                # Only the wake word was said, leave it on screen while waiting for the rest
                console.finish(line.text)
            else:
                console.cancel()
            return
        logging.info("Heard: %s", text)
        console.finish(text)
        input_state.queue_message(text)

    # Opens the microphone here, so a missing microphone stops startup with a clear error
    recognizer.start(on_line, on_partial)

    if output_state:
        threading.Thread(target=mute_loop, args=(recognizer, output_state), name="input-mute").start()
    threading.Thread(target=keyboard_loop, args=(input_state, console), name="input-keyboard").start()


def mute_loop(recognizer: SpeechRecognizer, output_state: OutputState):
    """
    Stop the robot from hearing itself, there is no echo cancellation on the microphone.
    """
    muted = False
    unmute_at = 0.0

    while True:
        if output_state.is_speaking():
            unmute_at = time.monotonic() + MUTE_TAIL_SECONDS

        should_mute = time.monotonic() < unmute_at
        if should_mute != muted:
            recognizer.mute(should_mute)
            muted = should_mute

        time.sleep(MUTE_POLL_SECONDS)


def keyboard_loop(input_state: InputState, console: SpeechConsole):
    """
    Typed lines are accepted alongside speech, and do not need the wake word.
    """
    while True:
        try:
            typed = input()
        except EOFError:
            logging.info("No keyboard attached, typed input is off")
            return

        # The keyboard is paused while a spoken line is coming in
        if not console.active:
            input_state.queue_message(typed)
