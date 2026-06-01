from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

# See https://cloud.google.com/text-to-speech/docs/voices for all voices.
streaming_config = texttospeech.StreamingSynthesizeConfig(
    voice=texttospeech.VoiceSelectionParams(
        name="en-US-Chirp3-HD-Charon",
        language_code="en-US",
    )
)

# Set the config for your stream. The first request must contain your config, and then each subsequent request must contain text.
config_request = texttospeech.StreamingSynthesizeRequest(
    streaming_config=streaming_config
)

text_iterator = [
    "Hello there. ",
    "How are you ",
    "today? It's ",
    "such nice weather outside.",
]

# Request generator. Consider using Gemini or another LLM with output streaming as a generator.
def request_generator():
    yield config_request
    for text in text_iterator:
        yield texttospeech.StreamingSynthesizeRequest(
            input=texttospeech.StreamingSynthesisInput(text=text)
        )

streaming_responses = client.streaming_synthesize(request_generator())

for response in streaming_responses:
    print(f"Audio content size in bytes is: {len(response.audio_content)}")