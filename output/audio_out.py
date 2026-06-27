"""Stream raw PCM audio to the speakers via ALSA (aplay).

Built for the Raspberry Pi Codec Zero. Audio is written to the ALSA `default`
device which, per ~/.asoundrc, resamples to the codec's native 48 kHz stereo --
so you can feed it whatever rate your source produces.

Typical use with a chunked / streaming source (e.g. Google Cloud streaming TTS,
which yields 24 kHz mono 16-bit PCM):

    from output.audio_out import PcmPlayer

    with PcmPlayer(rate=24000, channels=1) as player:
        for response in streaming_responses:
            player.write(response.audio_content)

The `with` block blocks on exit until all buffered audio has finished playing.
"""
from __future__ import annotations

import subprocess


class PcmPlayer:
    """Pipes raw (headerless) PCM bytes to `aplay` for low-latency playback."""

    def __init__(
        self,
        rate: int = 24000,
        channels: int = 1,
        fmt: str = "S16_LE",
        device: str = "default",
    ):
        self._args = [
            "aplay", "-q",
            "-D", device,
            "-f", fmt,
            "-r", str(rate),
            "-c", str(channels),
        ]
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> "PcmPlayer":
        self._proc = subprocess.Popen(self._args, stdin=subprocess.PIPE)
        return self

    def write(self, pcm_bytes: bytes) -> None:
        """Write one chunk of PCM. Call repeatedly as chunks stream in."""
        if not (self._proc and self._proc.stdin):
            raise RuntimeError("PcmPlayer must be used as a context manager")
        self._proc.stdin.write(pcm_bytes)

    def __exit__(self, *exc) -> None:
        if self._proc and self._proc.stdin:
            self._proc.stdin.close()   # signal end-of-stream to aplay
            self._proc.wait()          # block until playback finishes
        self._proc = None


if __name__ == "__main__":
    # Demo: stream a WAV file's PCM in small chunks, mimicking how a network
    # TTS stream would arrive. Usage: python output/audio_out.py [file.wav]
    import sys
    import wave

    path = sys.argv[1] if len(sys.argv) > 1 else "output/corporate-trainer.wav"
    with wave.open(path, "rb") as wf:
        with PcmPlayer(rate=wf.getframerate(), channels=wf.getnchannels()) as player:
            while chunk := wf.readframes(4096):
                player.write(chunk)
