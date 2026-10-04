"""Text to speech using Google AI Studio (Gemini TTS).

Yields raw 24 kHz mono 16-bit PCM chunks, ready to hand to PcmPlayer:

    from output.audio_out import PcmPlayer
    from output.speech import SAMPLE_RATE, CHANNELS, SpeechSynthesizer

    synthesizer = SpeechSynthesizer.from_config(config)
    with PcmPlayer(rate=SAMPLE_RATE, channels=CHANNELS) as player:
        for chunk in synthesizer.stream("Good morning."):
            player.write(chunk)
"""
import base64
import os
from typing import Iterator
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.8-flash-lite-tts"
DEFAULT_VOICE = "Finn"
DEFAULT_STYLE = ""

# Streaming responses are headerless PCM in this format
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2

REQUEST_TIMEOUT_SECONDS = 30.0

# Failures that get one more try. 429 is left out on purpose: when the quota is used up Gemini asks
# for a wait of hours, and the SDK sleeps for as long as it is told to, inside the request. That left
# the output thread stuck without an error, and the microphone muted for as long as it was "speaking".
RETRY_ATTEMPTS = 1
RETRY_STATUS_CODES = [408, 500, 502, 503, 504]

# The prebuilt voices listed in Google's docs. Custom voice ids are also accepted by the API.
PREBUILT_VOICES = {
    "Zephyr": "bright", "Puck": "upbeat", "Charon": "informative", "Kore": "firm", "Fenrir": "excitable",
    "Leda": "youthful", "Orus": "firm", "Aoede": "breezy", "Callirrhoe": "easy-going", "Autonoe": "bright",
    "Enceladus": "breathy", "Iapetus": "clear", "Umbriel": "easy-going", "Algieba": "smooth",
    "Despina": "smooth", "Erinome": "clear", "Algenib": "gravelly", "Rasalgethi": "informative",
    "Laomedeia": "upbeat", "Achernar": "soft", "Alnilam": "firm", "Schedar": "even", "Gacrux": "mature",
    "Pulcherrima": "forward", "Achird": "friendly", "Zubenelgenubi": "casual", "Vindemiatrix": "gentle",
    "Sadachbia": "lively", "Sadaltager": "knowledgeable", "Sulafat": "warm",
}


class SpeechError(Exception):
    """Speech could not be synthesized."""


class SpeechSynthesizer:
    def __init__(self, model: str = DEFAULT_MODEL, voice: str = DEFAULT_VOICE, style: str = DEFAULT_STYLE):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise SpeechError(
                "GEMINI_API_KEY is not set. Add it to the .env file to use speech output (see .env.example)."
            )

        self.model = model
        self.voice = voice
        self.style = style
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(
                attempts=RETRY_ATTEMPTS, http_status_codes=RETRY_STATUS_CODES,
            )),
        )

    @classmethod
    def from_config(cls, config: dict) -> "SpeechSynthesizer":
        speech_config = config.get("speech", {})
        return cls(
            model=speech_config.get("model", DEFAULT_MODEL),
            voice=speech_config.get("voice", DEFAULT_VOICE),
            style=speech_config.get("style", DEFAULT_STYLE),
        )

    def stream(self, text: str) -> Iterator[bytes]:
        """
        Synthesize text, yielding PCM chunks as they arrive.
        """
        content = {"type": "text", "text": text}
        if self.style:
            content["annotations"] = [{"type": "speech_metadata", "style": self.style}]

        try:
            events = self.client.interactions.create(
                model=self.model,
                input=[{"type": "user_input", "content": [content]}],
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": self.voice}]},
                # Don't keep what the robot says on Google's servers
                store=False,
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            for event in events:
                if event.event_type != "step.delta" or event.delta.type != "audio":
                    continue
                if event.delta.data:
                    yield base64.b64decode(event.delta.data)
        except Exception as e:
            # The SDK's Interactions API errors are not part of its public interface, so catch broadly
            raise SpeechError(
                f"Gemini TTS request failed for model '{self.model}', voice '{self.voice}': {e}"
            ) from e
