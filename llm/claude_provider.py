import logging
import anthropic
from .llm_provider import BOOT_PROMPT, MAX_OUTPUT_TOKENS, REQUEST_TIMEOUT_SECONDS, require_api_key, split_system_messages
from .llm_types import (
    ActionSpec, LlmAuthError, LlmRequestError, LlmResponse, LlmUnavailableError, Message, ToolCall,
)


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str):
        require_api_key("ANTHROPIC_API_KEY", self.name)
        self.model = model
        # Reads ANTHROPIC_API_KEY from the environment
        self.client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS)

    def chat(self, messages: list[Message], tools: list[ActionSpec]) -> LlmResponse:
        system_text, conversation = split_system_messages(messages)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_text,
                tools=[
                    {"name": spec.name, "description": spec.description, "input_schema": spec.input_schema}
                    for spec in tools
                ],
                messages=self._to_claude(conversation),
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise LlmAuthError(f"Claude rejected the API key, check ANTHROPIC_API_KEY: {e.message}") from e
        except anthropic.RateLimitError as e:
            raise LlmUnavailableError(f"Claude rate limit reached: {e.message}") from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise LlmUnavailableError(f"Claude server error ({e.status_code}): {e.message}") from e
            raise LlmRequestError(f"Claude rejected the request ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LlmUnavailableError(f"Could not reach Claude: {e}") from e

        logging.debug("Claude %s: stop_reason=%s, input_tokens=%s, output_tokens=%s", self.model,
                      response.stop_reason, response.usage.input_tokens, response.usage.output_tokens)

        if response.stop_reason in ("max_tokens", "refusal"):
            logging.warning("Claude stopped early, stop_reason=%s", response.stop_reason)

        text = "".join(block.text for block in response.content if block.type == "text")
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            for block in response.content if block.type == "tool_use"
        ]
        return LlmResponse(Message(role="assistant", content=text, tool_calls=tool_calls, provider=self.name))

    def _to_claude(self, conversation: list[Message]) -> list[dict]:
        claude_messages = []

        for message in conversation:
            if message.role == "tool":
                block = {"type": "tool_result", "tool_use_id": message.tool_call_id, "content": message.content}
                previous = claude_messages[-1] if claude_messages else None
                # All results for one assistant turn must be sent together in a single user message
                if previous and previous["role"] == "user" and isinstance(previous["content"], list):
                    previous["content"].append(block)
                else:
                    claude_messages.append({"role": "user", "content": [block]})

            elif message.role == "assistant":
                blocks = []
                if message.content:
                    blocks.append({"type": "text", "text": message.content})
                for tc in message.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                if blocks:
                    claude_messages.append({"role": "assistant", "content": blocks})

            else:
                previous = claude_messages[-1] if claude_messages else None
                # Text arriving right after tool results joins them, keeping the results first in the turn
                if previous and previous["role"] == "user" and isinstance(previous["content"], list):
                    previous["content"].append({"type": "text", "text": message.content})
                else:
                    claude_messages.append({"role": "user", "content": message.content})

        if not claude_messages or claude_messages[0]["role"] != "user":
            claude_messages.insert(0, {"role": "user", "content": BOOT_PROMPT})

        return claude_messages
