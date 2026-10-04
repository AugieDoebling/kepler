"""Try out speech to text models and the microphone without running the whole robot.

Defaults come from the "listening" block of kepler_config.json. Works from the
repo root or from inside input/. Stop with Ctrl-C:

    python listen_test.py                            # listen, print each line as it completes
    python listen_test.py --model small-streaming    # another model
    python listen_test.py --partial                  # also show the text while it is being spoken
    python listen_test.py --wake-word ""             # show every line as accepted
    python listen_test.py --list-devices             # show the microphones
    python listen_test.py --device 2                 # use a specific microphone
    python listen_test.py --sample-rate 48000        # ask the microphone for a specific rate
    python listen_test.py --file heard.wav           # transcribe a recording in place of the microphone
    python listen_test.py --list-models              # show the model names
"""
import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Replace this script's own folder on the path, it holds nothing that should be imported by bare name
sys.path[0] = REPO_ROOT

from input.recognizer import (
    DEFAULT_LANGUAGE, DEFAULT_MODEL, DEFAULT_UPDATE_INTERVAL_SECONDS, MODEL_NAMES, ListenError, SpeechRecognizer,
)
from input.wake_word import DEFAULT_WAKE_WORD, DEFAULT_WINDOW_SECONDS, WakeWordFilter


def load_listening_config() -> dict:
    config_path = os.path.join(REPO_ROOT, "kepler_config.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        return json.load(f).get("listening", {})


def parse_device(device):
    # Devices can be given by index or by name
    if isinstance(device, str) and device.isdigit():
        return int(device)
    return device


def main():
    listening_config = load_listening_config()

    parser = argparse.ArgumentParser(description="Try out speech to text models and the microphone.")
    parser.add_argument("--model", default=listening_config.get("model", DEFAULT_MODEL),
                        help="speech to text model (default: from kepler_config.json)")
    parser.add_argument("--wake-word", default=listening_config.get("wake_word", DEFAULT_WAKE_WORD),
                        help="wake word, or \"\" for none (default: from kepler_config.json)")
    parser.add_argument("--device", default=listening_config.get("device"),
                        help="microphone index or name (default: from kepler_config.json, else the system default)")
    parser.add_argument("--sample-rate", type=int, default=listening_config.get("sample_rate"),
                        help="sample rate to ask the microphone for")
    parser.add_argument("--update-interval", type=float,
                        default=listening_config.get("update_interval", DEFAULT_UPDATE_INTERVAL_SECONDS),
                        help="seconds of audio between transcription passes")
    parser.add_argument("--partial", action="store_true", help="also show the text while it is being spoken")
    parser.add_argument("--file", metavar="FILE.wav", help="transcribe a recording in place of the microphone")
    parser.add_argument("--list-devices", action="store_true", help="print the audio devices and exit")
    parser.add_argument("--list-models", action="store_true", help="print the model names and exit")
    args = parser.parse_args()

    if args.list_models:
        print("\n".join(MODEL_NAMES))
        return 0

    if args.list_devices:
        import sounddevice
        print(sounddevice.query_devices())
        return 0

    wake_word = WakeWordFilter(args.wake_word, listening_config.get("wake_word_window_seconds", DEFAULT_WINDOW_SECONDS))

    print(f"model:     {args.model}")
    print(f"wake word: {args.wake_word or '(none)'}")

    def on_line(line):
        accepted = wake_word.filter(line.text) is not None
        print(f"{'-->' if accepted else '   '} {line.text}")
        print(f"      {line.duration:.1f}s of speech, last transcription pass took "
              f"{line.last_transcription_latency_ms}ms, {'sent to the LLM' if accepted else 'ignored'}")

    def on_partial(text):
        print(f"  ... {text}")

    try:
        recognizer = SpeechRecognizer(
            model=args.model,
            language=listening_config.get("language", DEFAULT_LANGUAGE),
            device=parse_device(args.device),
            sample_rate=args.sample_rate,
            update_interval=args.update_interval,
            keyterms=[args.wake_word],
            options=listening_config.get("options"),
        )
        start = time.perf_counter()
        recognizer.load()
        print(f"model loaded in {time.perf_counter() - start:.1f}s")

        if args.file:
            from moonshine_voice import load_wav_file
            samples, sample_rate = load_wav_file(args.file)
            start = time.perf_counter()
            recognizer.transcribe(samples, sample_rate, on_line, on_partial if args.partial else None)
            print(f"{len(samples) / sample_rate:.1f}s of audio transcribed in {time.perf_counter() - start:.1f}s")
            return 0

        recognizer.start(on_line, on_partial if args.partial else None)
    except ListenError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1

    print("Listening, Ctrl-C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        recognizer.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
