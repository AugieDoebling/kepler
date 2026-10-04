"""Speech to text on the device using Moonshine.

Listens to the microphone, works out when a stretch of speech has ended, and
calls back with the transcribed line:

    from input.recognizer import SpeechRecognizer

    recognizer = SpeechRecognizer.from_config(config)
    recognizer.load()                                  # downloads the model the first time
    recognizer.start(lambda line: print(line.text))

Nothing leaves the machine. The first load of a model needs an internet
connection to download it; after that it runs offline.
"""
import logging
from typing import Callable, Optional, Sequence
from moonshine_voice import MicTranscriber, MoonshineError, ModelArch, TranscriptLine, string_to_model_arch
from moonshine_voice import model_arch_to_string

DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "en"

# Seconds of audio between transcription passes. The end of a line is only noticed on a pass,
# so a smaller value means a quicker response, at the cost of more CPU while someone is speaking.
DEFAULT_UPDATE_INTERVAL_SECONDS = 0.3

MODEL_NAMES = [model_arch_to_string(arch) for arch in ModelArch]


class ListenError(Exception):
    """Speech input could not be set up."""


class SpeechRecognizer:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        language: str = DEFAULT_LANGUAGE,
        device: Optional[int | str] = None,
        sample_rate: Optional[int] = None,
        update_interval: float = DEFAULT_UPDATE_INTERVAL_SECONDS,
        keyterms: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
    ):
        try:
            self._model_arch = string_to_model_arch(model)
        except ValueError:
            raise ListenError(
                f"Unknown listening model '{model}'. Expected one of: {', '.join(MODEL_NAMES)}"
            ) from None

        self.model = model
        self.language = language
        self.device = device
        self.sample_rate = sample_rate
        self.update_interval = update_interval
        self.keyterms = [term for term in (keyterms or []) if term]
        self.options = options or {}
        self._mic: Optional[MicTranscriber] = None

    @classmethod
    def from_config(cls, config: dict) -> "SpeechRecognizer":
        listening_config = config.get("listening", {})
        wake_word = listening_config.get("wake_word", "Kepler")
        return cls(
            model=listening_config.get("model", DEFAULT_MODEL),
            language=listening_config.get("language", DEFAULT_LANGUAGE),
            device=listening_config.get("device"),
            sample_rate=listening_config.get("sample_rate"),
            update_interval=listening_config.get("update_interval", DEFAULT_UPDATE_INTERVAL_SECONDS),
            # Nudge the model towards spelling the wake word the way the filter expects
            keyterms=[wake_word],
            options=listening_config.get("options"),
        )

    def load(self):
        """
        Download the model if it is not cached yet, and open it. Blocks until done.
        """
        mic = (
            MicTranscriber()
            .language(self.language)
            .model_arch(self._model_arch)
            .update_interval(self.update_interval)
            .device(self.device)
        )
        if self.sample_rate:
            mic.samplerate(self.sample_rate)
        if self.options:
            mic.options(self.options)

        try:
            mic.load()
        except Exception as e:
            raise ListenError(
                f"Could not load the '{self.model}' listening model for language '{self.language}': {e}"
            ) from e
        self._mic = mic

        # Only the streaming models can be biased towards key terms, the others work without it
        if self.keyterms and "streaming" in self.model:
            try:
                mic.set_keyterms(self.keyterms)
            except MoonshineError as e:
                logging.warning("Key terms %s not applied to model %s: %s", self.keyterms, self.model, e)

    def start(self, on_line: Callable[[TranscriptLine], None],
              on_partial: Optional[Callable[[str], None]] = None):
        """
        Open the microphone. on_line is called, on Moonshine's own thread, each time the speaker pauses.
        """
        mic = self._add_callbacks(on_line, on_partial)
        try:
            mic.start()
        except Exception as e:
            raise ListenError(f"Could not open the microphone (device: {self.device or 'default'}): {e}") from e

    def transcribe(self, samples: Sequence[float], sample_rate: int,
                   on_line: Callable[[TranscriptLine], None],
                   on_partial: Optional[Callable[[str], None]] = None, chunk_seconds: float = 0.1):
        """
        Run recorded mono audio through the same model in place of the microphone. Blocks until done.
        """
        mic = self._add_callbacks(on_line, on_partial)
        chunk_size = int(sample_rate * chunk_seconds)
        mic.mic_stream.start()
        for start in range(0, len(samples), chunk_size):
            mic.mic_stream.add_audio(samples[start:start + chunk_size], sample_rate)
        mic.mic_stream.stop()

    def mute(self, muted: bool):
        """Ignore the microphone without closing it, used while the robot itself is speaking."""
        if self._mic:
            self._mic.mute(muted)

    def close(self):
        if self._mic:
            self._mic.close()
            self._mic = None

    def _add_callbacks(self, on_line, on_partial) -> MicTranscriber:
        if self._mic is None:
            raise ListenError("SpeechRecognizer.load() must be called first")
        self._mic.on_line(on_line)
        if on_partial:
            self._mic.on_text(on_partial)
        self._mic.on_error(lambda error: logging.error("Speech recognition failed: %s", error))
        return self._mic
