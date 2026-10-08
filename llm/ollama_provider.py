import logging
import uuid
import ollama
from .llm_provider import BOOT_PROMPT
from .llm_types import ActionSpec, LlmRequestError, LlmResponse, LlmUnavailableError, Message, ToolCall


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str):
        self.model = model

    def chat(self, messages: list[Message], tools: list[ActionSpec]) -> LlmResponse:
        try:
            response: ollama.ChatResponse = ollama.chat(
                model=self.model,
                messages=self._to_ollama_messages(messages),
                tools=[spec.func for spec in tools],
            )
        except ConnectionError as e:
            raise LlmUnavailableError(f"Could not reach Ollama: {e}") from e
        except ollama.ResponseError as e:
            raise LlmRequestError(f"Ollama rejected the request: {e}") from e

        logging.debug("Ollama %s: done_reason=%s, prompt_tokens=%s, output_tokens=%s", self.model,
                      response.done_reason, response.prompt_eval_count, response.eval_count)

        tool_calls = [
            # Ollama tool calls have no id, so make one up for the other providers' benefit.
            ToolCall(id=f"ollama_{uuid.uuid4().hex}", name=tc.function.name, arguments=dict(tc.function.arguments))
            for tc in (response.message.tool_calls or [])
        ]
        return LlmResponse(Message(
            role="assistant",
            content=response.message.content or "",
            tool_calls=tool_calls,
            provider=self.name,
        ))

    def _to_ollama_messages(self, messages: list[Message]) -> list[ollama.Message]:
        ollama_messages = [self._to_ollama(m) for m in messages]

        # The robot speaks first on boot, so give it a user turn to respond to after the system prompt
        first_turn = next((i for i, m in enumerate(messages) if m.role != "system"), len(messages))
        if first_turn == len(messages) or messages[first_turn].role != "user":
            ollama_messages.insert(first_turn, ollama.Message(role="user", content=BOOT_PROMPT))

        return ollama_messages

    def _to_ollama(self, message: Message) -> ollama.Message:
        if message.role == "tool":
            return ollama.Message(role="tool", content=message.content, tool_name=message.tool_name)

        if message.role == "assistant" and message.tool_calls:
            return ollama.Message(
                role="assistant",
                content=message.content,
                tool_calls=[
                    ollama.Message.ToolCall(
                        function=ollama.Message.ToolCall.Function(name=tc.name, arguments=tc.arguments)
                    )
                    for tc in message.tool_calls
                ],
            )

        return ollama.Message(role=message.role, content=message.content)
