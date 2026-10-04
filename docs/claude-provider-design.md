# Design: Claude and Gemini as additional LLM backends

Status: **implemented 2026-10-04; live tests against Ollama, Claude and Gemini still to run**

## Goal

Add two more ways for the LLM thread to get responses, each using the provider's lightest model:

| Backend | Model | Price per 1M tokens (input / output) | Notes |
|---|---|---|---|
| Ollama (default, unchanged) | `gemma4:e4b` | free, local | |
| Claude API | `claude-haiku-4-5` | $1.00 / $5.00 | |
| Gemini API | `gemini-3.5-flash-lite` | $0.30 / $2.50 | Free tier available |

Which backend is used is a startup config value; a runtime trigger for switching is out of scope.

`gemini-2.5-flash-lite` is cheaper ($0.10 / $0.40) but Google now limits it to projects that already used it, so a new key cannot rely on it. The model name is a config value, so you can try it.

## Decisions

Confirmed 2026-10-04:

1. **Claude account.** An API key created in the Claude Console (platform.claude.com), billed from prepaid credits there. A Claude.ai subscription is not used.
2. **Web tools.** `web_search` / `web_fetch` stay as Ollama's hosted functions for every backend (see [Tools](#tools)).
3. **Where keys live.** A gitignored `.env` file at the repo root, loaded at startup (see [Credentials](#credentials)).

4. **Google entry point.** A Gemini API key from Google AI Studio, stored as `GEMINI_API_KEY` in `.env`. Vertex AI is not used.
5. **Gemini tier.** Free tier for now. On the free tier Google may use prompts and responses to improve its products; moving to paid later is a billing setting on the Google side with no code change.
6. **Gemini endpoint.** `generateContent` (see [`GeminiProvider`](#geminiprovider-new-file-llmgemini_providerpy)).

## Current state

| File | Ollama coupling |
|---|---|
| [llm/llm_thread.py](../llm/llm_thread.py) | Calls `ollama.chat(model='gemma4:e4b', ...)` directly and reads `response.message.content` / `.tool_calls`. |
| [llm/llm_state.py](../llm/llm_state.py) | History is a list of `ollama.Message` objects. |
| [llm/actions.py](../llm/actions.py) | Passes raw Python functions as tools (Ollama derives the schema from the signature); `call_action` takes an Ollama tool-call object. |
| [main.py](../main.py) | Builds the system prompt as `ollama.Message(role='system', ...)`. |

So the Ollama types leak into four files. The hosted APIs differ from Ollama in ways that matter here:

| | Claude | Gemini |
|---|---|---|
| System prompt | Top-level `system` parameter | Separate system-instruction parameter |
| First message | Must be a `user` message | Needs a user turn to respond to |
| Tool definitions | Explicit JSON schema | Explicit JSON schema |
| Tool results | Every tool call must get a `tool_result` with a matching ID in the next `user` message, or the request fails | Each function call must be answered with a function response |
| Assistant role name | `assistant` | `model` |
| Extra state to replay | None on Haiku 4.5 (no thinking) | Opaque "thought signatures" the model returns must be sent back unchanged on later turns |

Two of these collide with today's loop: it makes its first call with only system messages (the robot speaks first), and a tool that returns `None` (e.g. `move`) records no result.

## Proposed design

### Shape

```
llm_thread.loop
      │  provider.chat(messages, tools) -> LlmResponse
      ▼
 LlmProvider (interface)
   ├── OllamaProvider   (default; today's behavior)
   ├── ClaudeProvider   (new)
   └── GeminiProvider   (new)
```

`LlmState` keeps the conversation in a backend-neutral format. Each provider translates that history to its own wire format on every call. Because the history is neutral, switching backends later needs no history conversion, which is what makes the future "trigger" cheap to add.

### Neutral types (new file `llm/llm_types.py`)

```python
@dataclass
class ToolCall:
    id: str            # provider's call id; generated for Ollama, which has none
    name: str
    arguments: dict

@dataclass
class Message:
    role: str                       # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)   # assistant only
    tool_call_id: str | None = None                            # tool only
    tool_name: str | None = None                               # tool only (Gemini needs the name)
    provider: str | None = None                                # which backend produced an assistant turn
    provider_data: Any = None                                  # opaque; replayed only to that same backend

@dataclass
class LlmResponse:
    message: Message                # the assistant turn to append to history
```

`provider_data` exists for Gemini's thought signatures: `GeminiProvider` stores the raw model turn there and replays it verbatim on later calls. Other providers ignore it.

### Provider interface (new file `llm/llm_provider.py`)

```python
class LlmProvider(Protocol):
    def chat(self, messages: list[Message], tools: list[ActionSpec]) -> LlmResponse: ...

def create_provider(config: dict) -> LlmProvider:
    # reads config["llm"]["provider"]; defaults to "ollama" when absent
```

Behavior shared by both hosted providers:

- **Boot turn.** When history has no user message yet, the provider prepends a synthetic one, e.g. `"(You have just powered on. Greet your friend.)"`, so the robot can still speak first. It is not stored in history.
- **System prompt.** The neutral `system` messages are joined with blank lines into the provider's system parameter.
- **Blank user input** is dropped from the request, since both hosted APIs reject empty text.
- **Timeout 30 s.** The SDK defaults are minutes long, which is too long for a robot to stand silent.
- **No streaming.** The response is short and consumed whole. Worth revisiting when the speech output thread exists.

### `OllamaProvider` (new file `llm/ollama_provider.py`)

A thin move of today's code: convert neutral messages to `ollama.Message`, call `ollama.chat`, convert the response back. Behavior is unchanged.

### `ClaudeProvider` (new file `llm/claude_provider.py`)

Uses the official `anthropic` Python SDK with a hand-written loop (the loop already lives in `llm_thread`, so the SDK's beta tool runner would fight it).

```python
self.client = anthropic.Anthropic()        # reads ANTHROPIC_API_KEY from the environment

response = self.client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system=system_text,
    tools=tool_schemas,
    messages=claude_messages,
)
```

| Neutral | Claude |
|---|---|
| `user` | `{"role": "user", "content": text}` |
| `assistant` with text and/or tool calls | `{"role": "assistant", "content": [text block, tool_use blocks...]}` |
| `tool` | `tool_result` block in a `user` message; consecutive tool messages are merged into one `user` message. |

- Text blocks become `Message.content`; `tool_use` blocks become `ToolCall`s (`block.id`, `block.name`, `block.input`).
- `stop_reason == "max_tokens"` or `"refusal"` is logged as a warning; whatever text came back is still used.
- `max_tokens=1024`: replies are capped at three spoken sentences by the system prompt; 1024 leaves room for a tool call plus text while bounding a runaway reply.
- No thinking and no `effort` parameter: Haiku 4.5 runs without thinking by default, which is what we want for latency, and it rejects `effort`.
- No prompt caching: the system prompt plus tools is far below Haiku's minimum cacheable size.

### `GeminiProvider` (new file `llm/gemini_provider.py`)

Uses Google's `google-genai` Python SDK (`from google import genai`; `genai.Client()`), with the key from `GEMINI_API_KEY`.

**Which Gemini endpoint.** Google now has two: the newer Interactions API, which it recommends for new projects, and the older `generateContent`, which it calls legacy but fully supported. I propose `generateContent`:

- It is stateless: we send the full history each call, which is exactly how the neutral history works.
- Nothing is stored on Google's side. The Interactions API stores each conversation by default (55 days on the paid tier, 1 day on free) unless turned off.
- If Google later retires it, only this one file changes.

| Neutral | Gemini |
|---|---|
| `user` | Content with role `user` and a text part |
| `assistant` produced by Gemini | The saved `provider_data` (raw model content, including thought signatures), replayed verbatim |
| `assistant` produced by another backend | Content with role `model`, rebuilt from text and function-call parts |
| `tool` | Function-response part (name plus result) in a `user` content; consecutive tool messages merged |

- Automatic function calling in the SDK is turned off; our loop executes tools.
- Thinking is left at the model's default, which is `minimal` on 3.5 Flash-Lite. It is not set explicitly because older Gemini models reject that parameter.
- Output cap equivalent to Claude's 1024 tokens.
- Blocked or empty responses (safety filter) are logged as a warning and treated as an empty reply.

The request types were checked against the installed `google-genai` 2.28.0. A real tool-calling round trip has not been run yet, because that needs a key.

### Tools

`Actions` becomes the single source of truth for all backends. Each action gets an explicit spec:

```python
@dataclass
class ActionSpec:
    name: str
    description: str
    input_schema: dict     # JSON schema
    func: Callable
```

- `OllamaProvider` passes `spec.func` (as today).
- `ClaudeProvider` and `GeminiProvider` pass the name, description, and schema in their own envelope.
- `call_action` changes from taking an Ollama tool-call object to `call_action(name: str, arguments: dict)`.

Three schemas are written by hand (`move`, `web_search`, `web_fetch`). That duplicates the docstrings slightly, but avoids depending on private schema-generation helpers in any SDK.

`web_search` / `web_fetch` stay as Ollama's Python functions and are offered to Claude and Gemini as ordinary client tools. Consequence: in hosted modes those two tools still call Ollama's hosted API (and need whatever Ollama credentials they need today). `move` has no such dependency.

### Loop changes in `llm/llm_thread.py`

- Replace the `ollama.chat` call with `provider.chat(messages, actions.get_specs())`.
- **Always** record a tool result, even when the action returns `None` (recorded as `"ok"`). Whether to immediately call the model again still depends on the action returning a value, so `move` behaves exactly as it does now.
- If an action raises, record the error text as the tool result instead of crashing the thread.
- Wrap `provider.chat` in error handling: on failure, log it, print a short fallback line, and fall through to waiting for user input rather than killing the thread.

Each provider maps its SDK's errors to three neutral exceptions so the loop does not import any SDK: `LlmAuthError` (bad or missing key; logged with which variable to check), `LlmUnavailableError` (rate limit, server error, offline), and `LlmRequestError` (anything else).

### Selecting the backend

New block in `kepler_config.json`; absent block means Ollama:

```json
"llm": {
    "provider": "ollama",
    "ollama_model": "gemma4:e4b",
    "claude_model": "claude-haiku-4-5",
    "gemini_model": "gemini-3.5-flash-lite"
}
```

`provider` is one of `ollama`, `claude`, `gemini`. `main.py` passes the loaded config to `create_provider`. An unknown value fails at startup with a clear error. A hosted provider is only constructed (and its SDK only imported) when selected, so Ollama-only runs need neither package nor any key.

## Credentials

- Keys are read from environment variables by the SDKs. They are never written to `kepler_config.json` (which is committed) and never logged.
- They are stored in a `.env` file at the repo root, loaded at startup with `python-dotenv`:
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  GEMINI_API_KEY=...
  ```
  Only the key for the selected provider needs to be present.
- `.env` is added to `.gitignore`. A committed `.env.example` documents both variables with placeholders.
- On the robot: `chmod 600 .env`.
- Startup check: if the selected provider's variable is unset, fail immediately with a message saying which one to set, rather than failing on the first request.
- Logging: `main.py` sets the root logger to DEBUG, which would pull the SDKs' and HTTP libraries' request-level debug output into the log file. I will set those loggers (`anthropic`, `google_genai`, `httpx`, `httpx2`, `httpcore`) to WARNING. Conversation content is still logged by our own code as it is today.
- Recommended on the provider side: a dedicated key for the robot, and a spend limit (Claude Console workspace limit; Google Cloud budget), so a lost SD card or a runaway loop has a bounded cost.

## Files changed

| File | Change |
|---|---|
| `llm/llm_types.py` | **New.** `Message`, `ToolCall`, `LlmResponse`, neutral exceptions. |
| `llm/llm_provider.py` | **New.** `LlmProvider` protocol, `create_provider(config)`. |
| `llm/ollama_provider.py` | **New.** Today's Ollama call, behind the interface. |
| `llm/claude_provider.py` | **New.** Anthropic client, message/tool translation, response parsing. |
| `llm/gemini_provider.py` | **New.** Google GenAI client, message/tool translation, signature replay. |
| `llm/llm_state.py` | Use the neutral `Message` instead of `ollama.Message`. |
| `llm/llm_thread.py` | Take a provider; always record tool results; error handling. |
| `llm/actions.py` | `ActionSpec` list with schemas; `call_action(name, arguments)`. |
| `main.py` | Neutral `Message` for the system prompt; load `.env`; build provider from config; quiet SDK loggers. |
| `kepler_config.json` | Add the `llm` block (provider `ollama`). |
| `requirements.txt` | Add `anthropic`, `google-genai`, `python-dotenv`. |
| `.gitignore` | Add `.env`. |
| `.env.example` | **New.** Placeholders for `ANTHROPIC_API_KEY` and `GEMINI_API_KEY`. |

`llm/llm_test.py` is not touched. `llm_state.py`, `llm_thread.py`, `main.py`, and `requirements.txt` have uncommitted edits; I will build on top of those, not revert them.

## Cost

Estimates, assuming about 1,000 input and under 100 output tokens per short call. The whole history is resent each turn and `LlmState` has no rolling window yet (existing TODO), so a long session costs more per call.

| | 100 short calls | 100 calls in one long session |
|---|---|---|
| Claude Haiku 4.5 | ~$0.15 | ~$0.80 |
| Gemini 3.5 Flash-Lite | ~$0.055 | ~$0.25 |

A `web_fetch` result can add thousands of tokens that are then resent for the rest of the session.

## Risks and things to know

- **Python version.** The current `anthropic` SDK needs Python 3.10+. The local `.venv` is 3.10.1; I have not checked what the Raspberry Pi runs, or `google-genai`'s minimum.
- **Privacy.** In either hosted mode, everything in the conversation (and later, anything transcribed from the microphone) leaves the robot. Ollama mode stays local. See decision 5 for Gemini's free tier.
- **Latency.** Network round trip instead of local inference; likely faster than `gemma4:e4b` on a Pi, but dependent on Wi-Fi.
- **No automatic fallback.** If the hosted API is unreachable, the robot says so and waits; it does not fall back to Ollama. Easy to add once the switch trigger exists.
- **Mid-conversation switching to Gemini.** Not in scope now, but relevant to the future trigger: assistant turns produced by another backend have no thought signatures. I have not confirmed how Gemini treats tool-call turns in history that lack them. If it rejects them, the fix is to flatten those older turns to plain text when sending to Gemini.
- **Personality drift.** The same system prompt will read differently on each model. Expect to tune the prompt after trying them.

## Verification plan

1. Default config: confirm Ollama behavior is unchanged (boot greeting, a reply, a `move` call).
2. For each of `claude` and `gemini` with a valid key: boot greeting, a multi-turn chat, a `move` call followed by another user turn (exercises the always-record-tool-result path), and a `web_search` call (exercises the tool-result round trip and, for Gemini, signature replay).
3. Hosted provider with no key: clear startup error.
4. Hosted provider with a bad key: clear logged auth error, thread stays alive.

Steps 2 and 4 make real API calls and cost a few cents in total.
