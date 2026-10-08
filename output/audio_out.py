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

On machines without `aplay` (macOS, for development) the chunks are collected
and played with `afplay` when the `with` block exits, so playback there is not
streamed.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import wave


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
        self._rate = rate
        self._channels = channels
        self._proc: subprocess.Popen | None = None
        self._buffer: bytearray | None = None

    def __enter__(self) -> "PcmPlayer":
        if shutil.which("aplay"):
            self._proc = subprocess.Popen(self._args, stdin=subprocess.PIPE)
        elif shutil.which("afplay"):
            self._buffer = bytearray()
        else:
            raise RuntimeError("No audio player found, expected aplay (Linux) or afplay (macOS)")
        return self

    def write(self, pcm_bytes: bytes) -> None:
        """Write one chunk of PCM. Call repeatedly as chunks stream in."""
        if self._buffer is not None:
            self._buffer.extend(pcm_bytes)
            return
        if not (self._proc and self._proc.stdin):
            raise RuntimeError("PcmPlayer must be used as a context manager")
        self._proc.stdin.write(pcm_bytes)

    def __exit__(self, *exc) -> None:
        if self._proc and self._proc.stdin:
            self._proc.stdin.close()   # signal end-of-stream to aplay
            exit_code = self._proc.wait()   # block until playback finishes
            if exit_code != 0:
                # aplay prints the reason on the terminal
                logging.error("aplay exited with code %s, the audio may not have played: %s",
                              exit_code, " ".join(self._args))
        self._proc = None

        if self._buffer:
            self._play_buffer_with_afplay()
        self._buffer = None

    def _play_buffer_with_afplay(self) -> None:
        # afplay needs a file, and only 16-bit PCM is handled here
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            with wave.open(path, "wb") as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)
                wf.setframerate(self._rate)
                wf.writeframes(bytes(self._buffer))
            exit_code = subprocess.run(["afplay", path]).returncode
            if exit_code != 0:
                logging.error("afplay exited with code %s, the audio may not have played", exit_code)
        finally:
            os.remove(path)


if __name__ == "__main__":
    # Demo: stream a WAV file's PCM in small chunks, mimicking how a network
    # TTS stream would arrive. Usage: python output/audio_out.py [file.wav]
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "output/corporate-trainer.wav"
    with wave.open(path, "rb") as wf:
        with PcmPlayer(rate=wf.getframerate(), channels=wf.getnchannels()) as player:
            while chunk := wf.readframes(4096):
                player.write(chunk)
