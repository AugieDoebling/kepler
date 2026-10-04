# Design: spoken input with on-device speech-to-text (Moonshine)

Status: **implemented 2026-10-04; checked with recorded speech and stand-in components, not yet run with a real microphone or on the Pi (verification steps 5 to 7)**

Decisions confirmed: wake word "Kepler"; `base` model, set in the config file; keyboard stays on; folder is `input/`.

## Goal

You speak to Kepler and he answers, with no keyboard.

- Speech is transcribed on the Raspberry Pi 5 itself. No cloud service, no key, no cost.
- When Kepler detects you have stopped speaking, the transcript goes to the LLM straight away.
- It works the same whichever LLM provider is configured.
- Kepler only responds to speech that includes his name.
- Kepler does not listen to himself: the microphone is ignored while he is speaking.
- A test script in `input/` lets you try the microphone and models without running the whole robot.

## Design

### Flow

```
microphone ──▶ Moonshine MicTranscriber  (muted while Kepler is speaking)
               voice detection + speech-to-text, on the Pi
                   │ "line completed" callback, with the text
                   ▼
              WakeWordFilter  (drops lines not addressed to Kepler)
                   │
                   ▼
keyboard thread ──typed line──▶  InputState  ──wait_for_message()──▶ llm_thread
```

- Moonshine does three jobs: it reads the microphone, detects when speech starts and stops, and transcribes. Each stretch of speech between pauses is a "line", and it calls back when a line is complete. That callback is the end-of-speech trigger.
- `llm_thread` no longer calls `input()` itself when audio input is on; it waits on `InputState`, which both the microphone and the keyboard feed.
- With `audio_input` off (the default, as today), nothing is started, Moonshine is not imported, and `llm_thread` behaves exactly as before.

### Config

```json
"audio_input": false,
"listening": {
    "model": "base",
    "language": "en",
    "wake_word": "Kepler",
    "wake_word_window_seconds": 6,
    "device": null,
    "sample_rate": null,
    "update_interval": 0.3,
    "options": {}
}
```

| Setting | Meaning |
|---|---|
| `audio_input` | The on/off switch. |
| `model` | `tiny`, `base`, `tiny-streaming`, `small-streaming` or `medium-streaming`. |
| `wake_word` | Lines without it are ignored. `""` turns the wake word off. |
| `wake_word_window_seconds` | After the wake word is said on its own, how long the next line is accepted without it. |
| `device` | Microphone index or name; `null` is the system default. `listen_test.py --list-devices` shows them. |
| `sample_rate` | Rate to ask the microphone for; `null` is 16 kHz, falling back to the device's own rate if it refuses. |
| `update_interval` | Seconds of audio between transcription passes. The end of a line is only noticed on a pass, so smaller is more responsive and uses more CPU. Moonshine's own default is 0.5. |
| `options` | Passed straight to Moonshine, for tuning such as `{"vad_threshold": "0.3"}`. |

A missing `listening` block, or any missing setting in it, falls back to the values above.

### Model

Moonshine's documentation gives these latencies on a Raspberry Pi 5:

| Model | Latency |
|---|---|
| Tiny Streaming | 210 ms |
| Tiny | 237 ms |
| Base | 350 ms |
| Small Streaming | 527 ms |

The page does not define exactly what is measured, and nothing has been run on the Pi yet. The test script reports timings so you can check.

The default is `base`, as you chose. There is no streaming version of Base for English, which has one consequence: only the streaming models can be nudged towards particular words, so `base` gets no help spelling "Kepler". In the test below it spelled it correctly anyway.

A model is downloaded the first time it is used (Base is about 135 MB) and then runs offline. The code and the English models are MIT licensed.

### Wake word (`input/wake_word.py`)

There is no ready-made wake word model for "Kepler", and speech-to-text is running anyway, so the wake word is matched against the transcript.

- A line containing "Kepler" anywhere is sent to the LLM as it was heard: "Kepler, what time is it?", "Thank you, Kepler."
- Near misses count ("Keppler", "Kepler's"). The match is deliberately loose, so the odd similar word, such as "keeper", will also wake him.
- "Kepler" on its own sends nothing, and the next line within 6 seconds is accepted without the wake word. This covers pausing after his name.
- Anything else is ignored, and written to the log file at debug level.
- Typed lines never need the wake word.

### `SpeechRecognizer` (`input/recognizer.py`)

Wraps Moonshine's `MicTranscriber`: applies the config, loads the model, opens the microphone, and calls back with each completed line.

This differs from the proposal, which had its own microphone capture class (`input/audio_in.py`). The installed Moonshine (0.1.5) turned out to have a `mute()` on its microphone class for exactly this purpose, and to handle a microphone that refuses 16 kHz, so the separate class was not needed.

**Sample rate on the Pi.** The Codec Zero has one clock for playback and recording, and `audio_out.py` plays at 48 kHz. I believe recording at a different rate while audio is playing would fail. If it does, set `"sample_rate": 48000`; Moonshine converts internally. This needs checking on the Pi.

### Not hearing himself

The Codec Zero has no echo cancellation, so while Kepler speaks the microphone picks up his voice. The design is half-duplex: he does not listen while he talks.

- `OutputState` gains `is_speaking()`. It is true from the moment text is queued until playback of the last queued utterance has finished, so there is no gap between the LLM replying and the microphone muting.
- While `is_speaking()` is true, and for 300 ms afterwards (room echo), the microphone is muted. That includes the wait for the TTS service before audio starts.
- With `audio_output` off there is nothing to mute.

The cost: you cannot interrupt Kepler mid-sentence. That needs a microphone with echo cancellation (see [Later](#later)).

### `InputState` (`input/input_state.py`)

A thread-safe queue of user messages, plus `start_input(config, output_state)`, mirroring `start_output`.

- `queue_message(text)`: called by the recognizer callback and by the keyboard thread. Blank text is ignored.
- `wait_for_message()`: blocks until at least one message is queued, then returns everything queued, joined with spaces. If you pause mid-thought and Moonshine splits it into two lines, or say something while the LLM is still thinking, it arrives as one user message, not two.

### Input threads (`input/input_thread.py`)

- Opens the microphone at startup. If the model cannot be loaded or the microphone cannot be opened, startup fails with a clear message.
- Once the wake word has been heard in a line that is still being spoken, the line is shown on the console as `--> <text>` and rewritten in place as more of it is recognised (`input/console.py`). When the line completes, the final text is printed and logged. A line that turns out not to contain the wake word after all is erased.
- While a spoken line is on screen the keyboard is paused: typed keys are not shown and not submitted, and anything typed in that time (or half typed just before) is thrown away.
- One small thread mutes and unmutes the microphone as Kepler speaks.
- One small thread reads typed lines and queues them. There is no `-->` prompt in this mode; just type and press Enter. If there is no keyboard (running headless), this thread exits quietly.

### LLM thread (`llm/llm_thread.py`)

`start_thread` and `loop` accept an optional `InputState`. The one line that changed:

```python
user_response = input_state.wait_for_message() if input_state else input("--> ")
```

### Startup (`main.py`)

`input_state = start_input(config, output_state)` next to the existing `start_output` call, passed on to `llm_thread.start_thread`.

### Test script (`input/listen_test.py`)

Runs from the repo root or from inside `input/`. Reads defaults from `kepler_config.json`. Stop with Ctrl-C.

```
python listen_test.py                            # listen, print each line as it completes
python listen_test.py --model small-streaming    # another model
python listen_test.py --partial                  # also show the text while it is being spoken
python listen_test.py --wake-word ""             # show every line as accepted
python listen_test.py --list-devices             # show the microphones
python listen_test.py --device 2                 # use a specific microphone
python listen_test.py --sample-rate 48000        # ask the microphone for a specific rate
python listen_test.py --file heard.wav           # transcribe a recording in place of the microphone
python listen_test.py --list-models              # show the model names
```

For each line it prints the text, how long the speech was, how long the last transcription pass took, and whether the wake word filter would send it to the LLM. `--file` gives a repeatable way to compare models on the Pi.

The proposal's `--save` option (record what the microphone heard) is not implemented; `arecord` on the Pi does that job.

## One-time setup on the Pi

1. `sudo apt install libportaudio2` (needed by `sounddevice`).
2. `pip install -r requirements.txt` in the venv.
3. Turn on the Codec Zero's built-in microphone. The board ships with mixer presets in Raspberry Pi's `Pi-Codec` repository; the one for this setup is `Codec_Zero_OnboardMIC_record_and_SPK_playback.state`, loaded with `sudo alsactl restore -f <path>`. If you loaded a playback-only preset when you set up the speaker, the microphone is currently off.
4. Run `python input/listen_test.py` once while online, to download the model and check the microphone.
5. Set `"audio_input": true`.

## Files changed

| File | Change |
|---|---|
| `input/recognizer.py` | **New.** `SpeechRecognizer`: Moonshine model and microphone, completed lines out. |
| `input/wake_word.py` | **New.** `WakeWordFilter`. |
| `input/console.py` | **New.** `SpeechConsole`: live display of a spoken line, keyboard pause. |
| `input/input_state.py` | **New.** `InputState` queue and `start_input`. |
| `input/input_thread.py` | **New.** Starts listening; mute thread; keyboard thread. |
| `input/listen_test.py` | **New.** Test script. |
| `output/output_state.py` | Add `is_speaking()` and `finish_output()`. |
| `output/output_thread.py` | Call `finish_output()` when an utterance has been spoken, skipped, or has failed. |
| `llm/llm_thread.py` | Accept an optional `InputState`; take the user turn from it. |
| `main.py` | Call `start_input` and pass the state on. |
| `kepler_config.json` | Add the `listening` block. `audio_input` stays false. |
| `requirements.txt` | Add `moonshine-voice` and `sounddevice`. |

## Cost

Free. No account, no key, no per-use charge.

## Risks and things to know

- **Latency is mostly the pause, not the transcription.** Moonshine has to hear a stretch of silence before it decides you have finished, and it only notices on a transcription pass. `update_interval` controls the passes. For the silence itself, the library accepts options named `vad_threshold`, `vad_window_duration`, `vad_hop_size`, `vad_look_behind_sample_count` and `vad_max_segment_duration`; I have not found their defaults or tried changing them. They can be set through `options`.
- **The wake word depends on the transcript.** If the microphone is poor enough that "Kepler" comes out as something unrecognisable, he will not respond. `listen_test.py` shows what was heard and whether it was accepted.
- **Servo noise.** The microphone sits on the robot. Walking and head movement may be detected as speech and produce junk transcripts, or mask your voice. If so, the first fix is to ignore the microphone while moving, the same way as while speaking.
- **Microphone quality.** One small microphone on the board, possibly inside a body, at conversational distance. Accuracy may be noticeably worse than Moonshine's published figures.
- **No interrupting.** See [Not hearing himself](#not-hearing-himself).
- **Simultaneous record and playback on the Codec Zero** is assumed to work at a shared 48 kHz. Untested.
- **Privacy.** Audio never leaves the Pi. The transcript goes to whichever LLM provider is configured, as typed text does today.
- **Python version on the Pi.** Tested here on Python 3.14, macOS. I have not checked that `moonshine-voice` installs on the Pi's Python.

## Later

Not part of this change:

- **A dedicated wake word model** (openWakeWord, or similar), which would let speech-to-text sleep until his name is heard.
- **A conversation window**, so follow-up questions straight after a reply do not need his name.
- **Interrupting Kepler.** A USB microphone with built-in echo cancellation (ReSpeaker Lite, ReSpeaker XVF3800) removes the need to mute, and a way to stop playback mid-utterance.
- **Smarter end-of-turn detection** (Pipecat Smart Turn), which judges whether you have finished your thought and not only that you paused.
- **Showing "listening" on the display.**

## Verification

Done on this Mac:

1. `audio_input` false: `start_input` returns nothing and Moonshine is not imported.
2. A recording made with the macOS `say` command (five sentences, some with "Kepler", some without, one that is only "Kepler") run through `listen_test.py --file` with `base` and `tiny-streaming`. Every sentence was transcribed correctly and split at the pauses, and the wake word filter accepted and ignored the right ones, including the line after a bare "Kepler". Synthetic speech in a silent recording is the easy case; it says nothing about the real microphone.
3. The wiring (`InputState`, wake word, mute thread, `llm_thread`) run with stand-ins for the recognizer, the LLM and the speaker: spoken lines reached the LLM, ignored lines did not, and the microphone was muted from the moment a reply was queued until 300 ms after it finished.

4. The live console display and keyboard pause, run in a pseudo-terminal with a stand-in recognizer: text typed before and after a spoken line was submitted, text typed during it was neither shown nor submitted, and a line that lost its wake word was erased.

Not done:

5. A real microphone. `python input/listen_test.py` on the Mac or the Pi; macOS will ask for microphone permission.
6. `main.py` with `audio_input` and `audio_output` both on: speak a turn, get a spoken reply, confirm Kepler's own speech is not transcribed, confirm a typed line still works.
7. On the Pi: the setup steps above, then 5 and 6. This is where the sample rate question and servo noise get answered.

## References

- Moonshine: https://github.com/moonshine-ai/moonshine and https://moonshine-voice.readthedocs.io/
- Moonshine on Raspberry Pi (latency table): https://mintlify.wiki/moonshine-ai/moonshine/platforms/raspberry-pi
- Codec Zero configuration: https://www.raspberrypi.com/documentation/accessories/audio.html
