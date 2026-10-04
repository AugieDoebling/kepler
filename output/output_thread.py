from output.audio_out import PcmPlayer
from output.output_state import OutputState
from output.speech import CHANNELS, SAMPLE_RATE, SpeechSynthesizer
import logging
import time
import threading


def start_thread(output_state: OutputState, synthesizer: SpeechSynthesizer):
    """
    Create a thread that is responsible for controlling speech and listening.
    """
    output_thread = threading.Thread(target=loop, args=(output_state, synthesizer))
    output_thread.start()


def loop(output_state: OutputState, synthesizer: SpeechSynthesizer):
    logging.info("Starting output thread with model %s, voice %s", synthesizer.model, synthesizer.voice)

    while True:
        text = output_state.pop_output()
        if text is None:
            time.sleep(0.2)
            continue

        try:
            if text.strip():
                speak(synthesizer, text)
        except Exception:
            # The text has already been printed, so a failure here only loses the audio
            logging.exception("Failed to speak: %s", text)
        finally:
            output_state.finish_output()


def speak(synthesizer: SpeechSynthesizer, text: str):
    """
    Synthesize text and play it, blocking until playback has finished.
    """
    with PcmPlayer(rate=SAMPLE_RATE, channels=CHANNELS) as player:
        for chunk in synthesizer.stream(text):
            player.write(chunk)
