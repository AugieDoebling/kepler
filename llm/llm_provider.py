import logging
import os
from datetime import datetime
from typing import Protocol
from .llm_types import ActionSpec, LlmAuthError, LlmResponse, Message

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

def time_of_day(now: datetime) -> str:
    if 5 <= now.hour < 12:
        return "morning"
    if 12 <= now.hour < 17:
        return "afternoon"
    if 17 <= now.hour < 22:
        return "evening"
    return "night"


def build_boot_prompt(now: datetime) -> str:
    return (
        f"(You have just powered on. It is {now.strftime('%A')} {time_of_day(now)}. "
        f"Greet whoever is there in a way that suits the time of day.)"
    )


# Hosted providers must be given a user turn to respond to, but the robot speaks first on boot.
# Built once at startup, so the first turn of the conversation stays the same on every later request.
BOOT_PROMPT = build_boot_prompt(datetime.now())
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_TOKENS = 1024


class LlmProvider(Protocol):
    name: str

    def chat(self, messages: list[Message], tools: list[ActionSpec]) -> LlmResponse:
        ...


def split_system_messages(messages: list[Message]):
    """
    Separate the system prompt from the conversation, for providers that take it as its own parameter.
    """
    system_text = "\n\n".join(m.content for m in messages if m.role == "system")
    # Hosted providers reject empty text, which would otherwise poison every later request
    conversation = [m for m in messages if m.role != "system" and not (m.role == "user" and not m.content.strip())]
    return system_text, conversation


def require_api_key(env_var: str, provider_name: str):
    if not os.environ.get(env_var):
        raise LlmAuthError(
            f"{env_var} is not set. Add it to the .env file to use the {provider_name} provider "
            f"(see .env.example)."
        )


def create_provider(config: dict) -> LlmProvider:
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", DEFAULT_PROVIDER)
    logging.info("Creating LLM provider '%s'. Boot prompt: %s", provider_name, BOOT_PROMPT)

    # Providers are imported lazily so that only the selected provider's package needs to be installed.
    if provider_name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(llm_config.get("ollama_model", DEFAULT_OLLAMA_MODEL))

    if provider_name == "claude":
        from .claude_provider import ClaudeProvider
        return ClaudeProvider(llm_config.get("claude_model", DEFAULT_CLAUDE_MODEL))

    if provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(llm_config.get("gemini_model", DEFAULT_GEMINI_MODEL))

    raise ValueError(f"Unknown llm provider '{provider_name}'. Expected one of: ollama, claude, gemini.")
