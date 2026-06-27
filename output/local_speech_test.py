"""Audio-setup test: play the bundled corporate-trainer WAV through the speakers.

Run whenever you want to confirm audio output is working end to end
(codec unmuted, ALSA routing, ~/.asoundrc resample fix):

    .venv/bin/python output/local_speech_test.py

Plays through the ALSA `default` device, which resamples to the codec's
native 48 kHz stereo. If you hear the clip, the audio setup is good.
"""
import os
import subprocess
import sys

WAV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corporate-trainer.wav")

if not os.path.exists(WAV_PATH):
    sys.exit(f"Test file not found: {WAV_PATH}")

print(f"Playing {WAV_PATH}\nYou should hear audio from the speakers (Ctrl+C to stop)...")
result = subprocess.run(["aplay", "-D", "default", WAV_PATH])
sys.exit(result.returncode)
