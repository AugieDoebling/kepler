from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    """
    A provider-neutral conversation message. Each provider translates these to its own wire format.
    """
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)  # assistant only
    tool_call_id: Optional[str] = None  # tool only
    tool_name: Optional[str] = None  # tool only
    provider: Optional[str] = None  # which provider produced an assistant message
    provider_data: Any = None  # opaque, only replayed to the provider that produced it


@dataclass
class LlmResponse:
    message: Message


@dataclass
class ActionSpec:
    name: str
    description: str
    input_schema: dict
    func: Callable


class LlmError(Exception):
    """Base class for provider failures."""


class LlmAuthError(LlmError):
    """The API key is missing, invalid, or lacks permission."""


class LlmUnavailableError(LlmError):
    """The provider could not be reached, is overloaded, or rate limited the request."""


class LlmRequestError(LlmError):
    """The provider rejected the request."""
