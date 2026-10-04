"""Try out text to speech voices, models and styles without running the whole robot.

Defaults come from the "speech" block of kepler_config.json, and the key from
GEMINI_API_KEY in .env. Works from the repo root or from inside output/:

    python speech_test.py                                    # configured voice, sample line
    python speech_test.py --voice Kore                       # another voice
    python speech_test.py --voice Kore Puck Charon           # same line in several voices
    python speech_test.py --text "Good morning, sir."        # custom line
    python speech_test.py --style "tired and a bit grumpy"   # speaking style
    python speech_test.py --model gemini-3.8-flash-tts       # another model
    python speech_test.py --save out.wav                     # also save the audio
    python speech_test.py --list-voices                      # show the prebuilt voice names
"""
import argparse
import json
import os
import sys
import time
import wave

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv
from output.audio_out import PcmPlayer
from output.speech import (
    CHANNELS, DEFAULT_MODEL, DEFAULT_STYLE, DEFAULT_VOICE, PREBUILT_VOICES, SAMPLE_RATE, SAMPLE_WIDTH_BYTES,
    SpeechError, SpeechSynthesizer,
)

DEFAULT_TEXT = "Good morning! I do hope you slept well. Shall I put the kettle on, or shall we get straight to work?"


def load_speech_config() -> dict:
    config_path = os.path.join(REPO_ROOT, "kepler_config.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        return json.load(f).get("speech", {})


def save_wav(path: str, pcm: bytes):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH_BYTES)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def speak(synthesizer: SpeechSynthesizer, text: str) -> bytes:
    """Play the text, print timings, and return the audio that was played."""
    pcm = bytearray()
    start = time.perf_counter()
    first_audio_seconds = None

    with PcmPlayer(rate=SAMPLE_RATE, channels=CHANNELS) as player:
        for chunk in synthesizer.stream(text):
            if first_audio_seconds is None:
                first_audio_seconds = time.perf_counter() - start
            pcm.extend(chunk)
            player.write(chunk)
        generated_seconds = time.perf_counter() - start

    if first_audio_seconds is None:
        raise SpeechError("The request succeeded but returned no audio")

    audio_seconds = len(pcm) / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH_BYTES)
    print(f"  first audio after {first_audio_seconds:.2f}s, all audio after {generated_seconds:.2f}s, "
          f"{audio_seconds:.1f}s of speech")
    return bytes(pcm)


def main():
    speech_config = load_speech_config()

    parser = argparse.ArgumentParser(description="Try out text to speech voices, models and styles.")
    parser.add_argument("--voice", nargs="+", default=[speech_config.get("voice", DEFAULT_VOICE)],
                        help="one or more voice names or custom voice ids (default: from kepler_config.json)")
    parser.add_argument("--model", default=speech_config.get("model", DEFAULT_MODEL),
                        help="TTS model (default: from kepler_config.json)")
    parser.add_argument("--style", default=speech_config.get("style", DEFAULT_STYLE),
                        help="speaking style, e.g. \"a warm, whimsical English butler\"")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="the line to speak")
    parser.add_argument("--save", metavar="FILE.wav",
                        help="also save the audio; with several voices the voice name is added to the file name")
    parser.add_argument("--list-voices", action="store_true", help="print the prebuilt voice names and exit")
    args = parser.parse_args()

    if args.list_voices:
        for name, description in PREBUILT_VOICES.items():
            print(f"{name:15} {description}")
        return 0

    load_dotenv(os.path.join(REPO_ROOT, ".env"))

    print(f"model: {args.model}")
    print(f"style: {args.style or '(none)'}")
    print(f"text:  {args.text}")

    failures = 0
    for voice in args.voice:
        print(f"voice: {voice}")
        try:
            pcm = speak(SpeechSynthesizer(model=args.model, voice=voice, style=args.style), args.text)
        except SpeechError as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            failures += 1
            continue

        if args.save:
            path = args.save
            if len(args.voice) > 1:
                base, extension = os.path.splitext(args.save)
                path = f"{base}-{voice}{extension}"
            save_wav(path, pcm)
            print(f"  saved {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
