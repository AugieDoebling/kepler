from display.display_state import DisplayState, EyeState
from output.audio_out import PcmPlayer
from output.output_state import OutputState
from output.speech import CHANNELS, SAMPLE_RATE, SpeechSynthesizer
from typing import Optional
import logging
import time
import threading


def start_thread(output_state: OutputState, synthesizer: SpeechSynthesizer,
                 display_state: Optional[DisplayState] = None):
    """
    Create a thread that is responsible for controlling speech and listening.
    """
    output_thread = threading.Thread(target=loop, args=(output_state, synthesizer, display_state), name="output")
    output_thread.start()


def loop(output_state: OutputState, synthesizer: SpeechSynthesizer, display_state: Optional[DisplayState] = None):
    logging.info("Starting output thread with model %s, voice %s", synthesizer.model, synthesizer.voice)

    while True:
        text = output_state.pop_output()
        if text is None:
            time.sleep(0.2)
            continue

        try:
            if text.strip():
                speak(synthesizer, text, display_state)
        except Exception:
            # The text has already been printed, so a failure here only loses the audio
            logging.exception("Failed to speak: %s", text)
        finally:
            output_state.finish_output()


def speak(synthesizer: SpeechSynthesizer, text: str, display_state: Optional[DisplayState] = None):
    """
    Synthesize text and play it, blocking until playback has finished.
    """
    logging.info("Speaking %d characters: %s", len(text), text)
    start = time.perf_counter()
    first_audio_seconds = None
    audio_bytes = 0

    try:
        with PcmPlayer(rate=SAMPLE_RATE, channels=CHANNELS) as player:
            for chunk in synthesizer.stream(text):
                if first_audio_seconds is None:
                    first_audio_seconds = time.perf_counter() - start
                    logging.debug("First audio arrived after %.2fs", first_audio_seconds)
                audio_bytes += len(chunk)
                # The display shows speaking from the first sound, not while waiting for the speech service
                if display_state:
                    display_state.set_eye_state(EyeState.SPEAKING)
                player.write(chunk)
    finally:
        if display_state:
            display_state.set_eye_state(EyeState.REGULAR)

    if first_audio_seconds is None:
        logging.warning("The speech service returned no audio, nothing was played")
        return
    # 16 bit samples
    audio_seconds = audio_bytes / (SAMPLE_RATE * CHANNELS * 2)
    logging.info("Spoke %.1fs of audio, first audio after %.2fs, finished after %.1fs",
                 audio_seconds, first_audio_seconds, time.perf_counter() - start)
