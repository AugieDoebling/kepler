"""Speech to text on the device using Moonshine.

Listens to the microphone, works out when a stretch of speech has ended, and
calls back with the transcribed line:

    from input.recognizer import SpeechRecognizer

    recognizer = SpeechRecognizer.from_config(config)
    recognizer.load()                                  # downloads the model the first time
    recognizer.start(lambda line: print(line.text))

Nothing leaves the machine. The first load of a model needs an internet
connection to download it; after that it runs offline.

The microphone is read through ALSA with `arecord`, the same way audio_out.py
plays through `aplay`. Moonshine's own MicTranscriber is not used: it records
through PortAudio, which Ubuntu builds with a PulseAudio backend that stops
PortAudio from starting at all when no PulseAudio server is running, and this
robot runs plain ALSA.
"""
import fcntl
import logging
import shutil
import subprocess
import threading
from typing import Callable, Optional, Sequence
import numpy as np
from moonshine_voice import Error, LineCompleted, LineTextChanged, Transcriber
from moonshine_voice import MoonshineError, ModelArch, TranscriptLine, string_to_model_arch
from moonshine_voice import get_model_for_language, model_arch_to_string

DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "en"

# The ALSA device to record from. `default` converts to whatever rate the codec really runs at.
DEFAULT_DEVICE = "default"
# The rate Moonshine works in, other rates are converted by it
DEFAULT_SAMPLE_RATE = 16000

# Seconds of audio between transcription passes. The end of a line is only noticed on a pass,
# so a smaller value means a quicker response, at the cost of more CPU while someone is speaking.
DEFAULT_UPDATE_INTERVAL_SECONDS = 0.3

# arecord is asked for 16 bit mono
BYTES_PER_SAMPLE = 2
# Room in the pipe from arecord, half a minute at 16 kHz. Nothing is read from it during a
# transcription pass, which can take seconds on the Pi, and arecord drops audio when it is full.
# A read returns all that is waiting, so the backlog from a pass arrives as one piece.
PIPE_BYTES = 1 << 20
# arecord gives up straight away when it cannot open the device, so one that lasts this long is recording
ARECORD_STARTUP_SECONDS = 0.5

MODEL_NAMES = [model_arch_to_string(arch) for arch in ModelArch]


class ListenError(Exception):
    """Speech input could not be set up."""


class SpeechRecognizer:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        language: str = DEFAULT_LANGUAGE,
        device: Optional[str] = None,
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
        self.device = device or DEFAULT_DEVICE
        self.sample_rate = sample_rate or DEFAULT_SAMPLE_RATE
        self.update_interval = update_interval
        self.keyterms = [term for term in (keyterms or []) if term]
        self.options = options or {}
        self._transcriber: Optional[Transcriber] = None
        self._stream = None
        self._arecord: Optional[subprocess.Popen] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._muted = False

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
        try:
            model_path, model_arch = get_model_for_language(self.language, self._model_arch)
            self._transcriber = Transcriber(str(model_path), model_arch, options=self.options or None)
            self._stream = self._transcriber.create_stream(self.update_interval)
        except Exception as e:
            raise ListenError(
                f"Could not load the '{self.model}' listening model for language '{self.language}': {e}"
            ) from e

        # Only the streaming models can be biased towards key terms, the others work without it
        if self.keyterms and "streaming" in self.model:
            try:
                self._transcriber.set_keyterms(self.keyterms)
            except MoonshineError as e:
                logging.warning("Key terms %s not applied to model %s: %s", self.keyterms, self.model, e)

    def start(self, on_line: Callable[[TranscriptLine], None],
              on_partial: Optional[Callable[[str], None]] = None):
        """
        Open the microphone. on_line is called, on the capture thread, each time the speaker pauses.
        """
        stream = self._add_callbacks(on_line, on_partial)
        if not shutil.which("arecord"):
            raise ListenError("Could not open the microphone: arecord was not found (sudo apt install alsa-utils)")

        arecord = subprocess.Popen(
            ["arecord", "-q", "-D", self.device, "-f", "S16_LE", "-r", str(self.sample_rate), "-c", "1", "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            arecord.wait(timeout=ARECORD_STARTUP_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        else:
            error = arecord.stderr.read().decode(errors="replace").strip()
            raise ListenError(f"Could not open the microphone (device: {self.device}): {error}")

        try:
            fcntl.fcntl(arecord.stdout, fcntl.F_SETPIPE_SZ, PIPE_BYTES)
        except OSError as e:
            logging.warning("The pipe from arecord stays at its default size, long lines may lose audio: %s", e)

        self._arecord = arecord
        stream.start()
        self._capture_thread = threading.Thread(
            target=self._capture_loop, args=(arecord, stream), name="input-capture", daemon=True)
        self._capture_thread.start()
        threading.Thread(target=self._arecord_log_loop, args=(arecord,), name="input-arecord-log", daemon=True).start()

    def transcribe(self, samples: Sequence[float], sample_rate: int,
                   on_line: Callable[[TranscriptLine], None],
                   on_partial: Optional[Callable[[str], None]] = None, chunk_seconds: float = 0.1):
        """
        Run recorded mono audio through the same model in place of the microphone. Blocks until done.
        """
        stream = self._add_callbacks(on_line, on_partial)
        chunk_size = int(sample_rate * chunk_seconds)
        stream.start()
        for start in range(0, len(samples), chunk_size):
            stream.add_audio(samples[start:start + chunk_size], sample_rate)
        stream.stop()

    def mute(self, muted: bool):
        """Ignore the microphone without closing it, used while the robot itself is speaking."""
        self._muted = muted

    def close(self):
        if self._arecord:
            arecord, self._arecord = self._arecord, None
            arecord.terminate()
            arecord.wait()
            # Let a transcription pass that is under way finish before the stream goes
            self._capture_thread.join()
        if self._stream:
            self._stream.close()
            self._stream = None
        if self._transcriber:
            self._transcriber.close()
            self._transcriber = None

    def _capture_loop(self, arecord: subprocess.Popen, stream):
        """
        Pass what arecord hears to Moonshine. A transcription pass runs inside add_audio every
        update_interval, the audio recorded in the meantime waits in the pipe.
        """
        leftover = b""
        while data := arecord.stdout.read1(PIPE_BYTES):
            data = leftover + data
            whole = len(data) - len(data) % BYTES_PER_SAMPLE
            leftover = data[whole:]
            if self._muted:
                continue
            samples = np.frombuffer(data[:whole], dtype="<i2").astype(np.float32) / 32768.0
            try:
                stream.add_audio(samples, self.sample_rate)
            except Exception as e:
                logging.error("Speech recognition failed: %s", e)

        if self._arecord is arecord:
            logging.error("The microphone stopped, arecord exited with code %s", arecord.wait())

    def _arecord_log_loop(self, arecord: subprocess.Popen):
        # Read as it comes, so that arecord never blocks on a full pipe. Overruns are reported here.
        for line in arecord.stderr:
            # It also complains about being stopped by close(), which is not worth reporting
            if self._arecord is arecord:
                logging.warning("arecord: %s", line.decode(errors="replace").strip())

    def _add_callbacks(self, on_line, on_partial):
        if self._stream is None:
            raise ListenError("SpeechRecognizer.load() must be called first")

        def listener(event):
            if isinstance(event, LineCompleted):
                on_line(event.line)
            elif isinstance(event, LineTextChanged) and on_partial:
                on_partial(event.line.text)
            elif isinstance(event, Error):
                logging.error("Speech recognition failed: %s", event.error)

        self._stream.add_listener(listener)
        return self._stream
