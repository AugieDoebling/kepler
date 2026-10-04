# Design: spoken output with Google AI Studio text-to-speech

Status: **implemented 2026-10-04; not yet run against the live TTS service or real speakers (verification steps 2 to 4)**

Decisions confirmed: keep `Finn` as the default voice and change it if the API rejects it; rewrite `output/speech_test.py` and drop `google-cloud-texttospeech`; add the `style` setting.

## Goal

Kepler speaks his replies aloud, using Google AI Studio (Gemini API) text-to-speech.

- The voice and the TTS model are config settings, defaulting to the `Finn` voice and `gemini-3.8-flash-lite-tts`.
- The TTS model is separate from the LLM. Speech works the same whether the LLM provider is Ollama, Claude, or Gemini.
- A test script in `output/` lets you try voices, models, and styles without running the whole robot.

## Decisions I need from you

1. **The `Finn` voice.** Google's TTS documentation lists 30 built-in voices and `Finn` is not one of them (the full list is in [Voices](#voices)). The page also describes custom voices you can design or clone, which get IDs like `voice_...`. Where did you see `Finn`? Possibilities:
   - It is a custom voice you created in AI Studio. Then the config needs its `voice_...` ID, not the display name.
   - It is a name from a different product or an AI Studio label the API docs don't list. Then the API may reject it.

   The design keeps `Finn` as the default as you asked, since the voice is just a config string. If the API rejects it, the test script will show that on the first run, and you can pick another. I have not called the API to check, because that would use your key.
2. **Replace `output/speech_test.py`?** You asked for the test script in "audio/output"; there is no `audio/` folder, so I am assuming `output/`. That folder already has a `speech_test.py`, an early experiment against the older Google Cloud Text-to-Speech service. I propose rewriting that file as the new test script. It is the only thing using the `google-cloud-texttospeech` package, so I would also drop that from `requirements.txt`.
3. **A speaking style.** Gemini TTS accepts an optional style description for the whole utterance (for example "a warm, whimsical English butler"). I propose a third config setting, `style`, defaulting to empty (the voice's natural delivery), so you can experiment with the test script first.

## Current state

| File | State |
|---|---|
| [llm/llm_thread.py](../llm/llm_thread.py) | Prints the reply to the console; has `# TODO: Call output state`. |
| [output/output_state.py](../output/output_state.py) | A thread-safe queue of text to speak. Exists, unused. |
| [output/output_thread.py](../output/output_thread.py) | A stub loop that polls the queue and does nothing. Not started by `main.py`. |
| [output/speech.py](../output/speech.py) | Empty. |
| [output/audio_out.py](../output/audio_out.py) | `PcmPlayer`: pipes raw audio to `aplay`. Works on the Raspberry Pi only; `aplay` does not exist on macOS. |
| [kepler_config.json](../kepler_config.json) | Already has `"audio_output": false`, currently read by nothing. |

So the queue and the player exist; what is missing is the synthesizer, the thread body, and the wiring.

## Proposed design

### Flow

```
llm_thread ──queue_output(text)──▶ OutputState ──▶ output_thread
                                                      │ SpeechSynthesizer.stream(text)
                                                      ▼
                                              Gemini TTS (streaming)
                                                      │ 24 kHz mono 16-bit audio chunks
                                                      ▼
                                                  PcmPlayer ──▶ speakers
```

- `llm_thread` still prints every reply. When `audio_output` is on, it also queues the text.
- `output_thread` takes one utterance at a time, so replies are spoken in order and never overlap.
- With `audio_output` off (the default, as today), no thread is started, no key is needed, and nothing changes.

### Config

```json
"audio_output": false,
"speech": {
    "model": "gemini-3.8-flash-lite-tts",
    "voice": "Finn",
    "style": ""
}
```

`audio_output` is the existing on/off switch. A missing `speech` block, or any missing setting in it, falls back to the defaults above.

### `SpeechSynthesizer` (fills in `output/speech.py`)

Uses the `google-genai` SDK already installed for the Gemini LLM provider, and the same `GEMINI_API_KEY` in `.env`. No new package, no new key.

Google's TTS models are served through its Interactions API (the newer of its two endpoints; the docs show no other way to call the 3.8 TTS models):

```python
stream = client.interactions.create(
    model="gemini-3.8-flash-lite-tts",
    input=[{"type": "user_input", "content": [{
        "type": "text",
        "text": text,
        "annotations": [{"type": "speech_metadata", "style": style}],   # only when style is set
    }]}],
    response_format={"type": "audio"},
    generation_config={"speech_config": [{"voice": "Finn"}]},
    store=False,
    stream=True,
)
for event in stream:
    if event.event_type == "step.delta" and event.delta.type == "audio":
        yield base64.b64decode(event.delta.data)
```

- **Streaming.** Audio arrives in chunks and playback starts on the first one, instead of waiting for the whole sentence to be generated.
- **`store=False`.** The Interactions API keeps each request on Google's servers by default (1 day on the free tier, 55 days on paid). This turns that off.
- **Timeout 30 s**, matching the LLM providers.
- The request shape above is from Google's current docs, and I confirmed the installed SDK (2.28.0) accepts these parameters. It has not been run against the live service.

### Playback (`output/audio_out.py`)

`PcmPlayer` keeps its interface. On the Pi it behaves exactly as now (streams to `aplay`). On macOS it collects the chunks into a temporary WAV file and plays it with the built-in `afplay` when the utterance ends. That means no streaming on the Mac, so speech starts slightly later there than on the robot, but it needs nothing installed.

### Output thread (`output/output_thread.py`)

- Pop text from the queue, synthesize, play, repeat. It blocks while audio plays.
- Blank text is skipped.
- If synthesis or playback fails (bad voice name, rate limit, offline, no audio device), the error is logged at ERROR level, which now also shows on stderr, and that utterance is skipped. The thread stays alive and the text was already printed.
- Fixes a small existing bug in the stub (`args=(output_state)` is missing a comma, so the thread would not start).

### Startup (`main.py`)

When `audio_output` is true: create `OutputState`, build the synthesizer, start the output thread, and pass the state to `llm_thread`. If `GEMINI_API_KEY` is missing, fail at startup with a clear message, the same way the LLM providers do.

### Test script (`output/speech_test.py`)

Runs from the repo root or from inside `output/`. Reads defaults from `kepler_config.json` and the key from `.env`.

```
python speech_test.py                                   # speak a sample line with the configured voice
python speech_test.py --voice Kore                      # try another voice
python speech_test.py --voice Kore Puck Charon          # same line in several voices, announced by name
python speech_test.py --text "Good morning, sir."       # custom line
python speech_test.py --style "tired and a bit grumpy"  # try a style
python speech_test.py --model gemini-3.8-flash-tts      # try the larger model
python speech_test.py --save out.wav                    # also save the audio
python speech_test.py --list-voices                     # print the built-in voice names
```

For each utterance it prints the voice, the time until the first audio arrived, and the audio length, so you can compare latency between models as well as how they sound.

## Voices

The 30 built-in voices Google documents, with its one-word descriptions:

Zephyr (bright), Puck (upbeat), Charon (informative), Kore (firm), Fenrir (excitable), Leda (youthful), Orus (firm), Aoede (breezy), Callirrhoe (easy-going), Autonoe (bright), Enceladus (breathy), Iapetus (clear), Umbriel (easy-going), Algieba (smooth), Despina (smooth), Erinome (clear), Algenib (gravelly), Rasalgethi (informative), Laomedeia (upbeat), Achernar (soft), Alnilam (firm), Schedar (even), Gacrux (mature), Pulcherrima (forward), Achird (friendly), Zubenelgenubi (casual), Vindemiatrix (gentle), Sadachbia (lively), Sadaltager (knowledgeable), Sulafat (warm).

The script's `--list-voices` prints this list. The config and `--voice` accept any string, so custom voice IDs work too.

## Files changed

| File | Change |
|---|---|
| `output/speech.py` | **Filled in.** `SpeechSynthesizer`: Gemini TTS client, streaming audio chunks. |
| `output/output_thread.py` | Implement the loop: pop, synthesize, play; error handling. |
| `output/audio_out.py` | macOS playback path alongside the existing `aplay` path. |
| `output/speech_test.py` | **Rewritten** as the voice test script (decision 2). |
| `llm/llm_thread.py` | Accept an optional `OutputState`; queue reply text as well as printing it. |
| `main.py` | Read `audio_output` and `speech`; start the output thread when enabled. |
| `kepler_config.json` | Add the `speech` block. Your uncommitted provider/model edits there are kept. |
| `.env.example` | Note that `GEMINI_API_KEY` is also used for speech. |
| `requirements.txt` | Remove `google-cloud-texttospeech` (decision 2). |

`output/output_state.py` and `output/local_speech_test.py` are not touched.

## Cost

Gemini 3.8 Flash-Lite TTS has a free tier. On the paid tier it is $0.50 per million input tokens and $6.00 per million audio output tokens, at 25 audio tokens per second of speech. That is about $0.009 per minute of speech, so a typical 8-second reply costs about a tenth of a cent, and 100 replies about 12 cents. Google's pricing page says both prices double on 1 January 2027.

## Risks and things to know

- **Free-tier rate limits.** Every spoken reply is one TTS request. Google's docs don't state the free-tier limits for this model, and TTS limits have historically been tight. If Kepler hits one, that reply is printed but not spoken.
- **Privacy.** Everything Kepler says is sent to Google for synthesis, even when the LLM is local Ollama. On the free tier Google may use it to improve its products.
- **Latency.** Speech adds a second network round trip after the LLM reply. I have no measurement; the test script reports time to first audio.
- **Speech and the prompt overlap.** The LLM loop does not wait for speech to finish before showing `-->` again. Harmless with keyboard input. Once microphone input exists, Kepler would hear himself, so input will need to pause while he speaks.
- **Markup in replies.** If the LLM emits asterisks or other markdown, the voice may read it oddly, and text in angle brackets (like `<sigh>`) is treated by the TTS model as a sound instruction. The system prompt already asks for speakable text only; I am not adding a text filter in this change.
- **Raspberry Pi playback** relies on the existing `aplay` setup described in `audio_out.py`. I can only test the macOS path here.

## Verification plan

1. `audio_output` false: confirm behavior is unchanged and no key is required.
2. Run the test script on this Mac with the default config, a second voice, a style, and `--save`. This answers the `Finn` question.
3. Run `main.py` with `audio_output` true and stationary mode on: boot greeting spoken, a multi-reply turn spoken in order.
4. Bad voice name and missing key: clear error, robot keeps running (or clear startup failure for the key).

Steps 2 to 4 use your `GEMINI_API_KEY` from `.env`, make a handful of free-tier requests, and play audio out loud on this Mac. I will not run them unless you say so; otherwise I will leave them for you to run.
