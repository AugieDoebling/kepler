import logging
import os
import uuid
import httpx
from google import genai
from google.genai import errors, types
from .llm_provider import BOOT_PROMPT, MAX_OUTPUT_TOKENS, REQUEST_TIMEOUT_SECONDS, require_api_key, split_system_messages
from .llm_types import (
    ActionSpec, LlmAuthError, LlmRequestError, LlmResponse, LlmUnavailableError, Message, ToolCall,
)

# Gemini does not always give function calls an id, so we make one up and must not send it back.
SYNTHETIC_ID_PREFIX = "gemini_noid_"


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str):
        require_api_key("GEMINI_API_KEY", self.name)
        self.model = model
        self.client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=int(REQUEST_TIMEOUT_SECONDS * 1000)),
        )

    def chat(self, messages: list[Message], tools: list[ActionSpec]) -> LlmResponse:
        system_text, conversation = split_system_messages(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_text,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=spec.name, description=spec.description, parameters_json_schema=spec.input_schema
                )
                for spec in tools
            ])],
            # Our loop runs the tools, not the SDK
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=self._to_gemini(conversation), config=config
            )
        except errors.APIError as e:
            if e.code in (401, 403) or "api key" in str(e.message).lower():
                raise LlmAuthError(f"Gemini rejected the API key, check GEMINI_API_KEY: {e.message}") from e
            if e.code == 429 or e.code >= 500:
                raise LlmUnavailableError(f"Gemini unavailable ({e.code}): {e.message}") from e
            raise LlmRequestError(f"Gemini rejected the request ({e.code}): {e.message}") from e
        except httpx.HTTPError as e:
            raise LlmUnavailableError(f"Could not reach Gemini: {e}") from e

        candidate = response.candidates[0] if response.candidates else None
        usage = response.usage_metadata
        logging.debug("Gemini %s: finish_reason=%s, prompt_tokens=%s, output_tokens=%s", self.model,
                      candidate.finish_reason if candidate else None,
                      usage.prompt_token_count if usage else None,
                      usage.candidates_token_count if usage else None)
        content = candidate.content if candidate else None
        parts = (content.parts or []) if content else []

        if not parts:
            logging.warning(
                "Gemini returned no content, finish_reason=%s prompt_feedback=%s",
                candidate.finish_reason if candidate else None, response.prompt_feedback,
            )
            return LlmResponse(Message(role="assistant", provider=self.name))

        text = "".join(part.text for part in parts if part.text and not part.thought)
        tool_calls = [
            ToolCall(
                id=part.function_call.id or f"{SYNTHETIC_ID_PREFIX}{uuid.uuid4().hex}",
                name=part.function_call.name,
                arguments=dict(part.function_call.args or {}),
            )
            for part in parts if part.function_call
        ]
        # The raw content carries thought signatures, which Gemini requires back unchanged on later turns
        return LlmResponse(Message(
            role="assistant", content=text, tool_calls=tool_calls, provider=self.name, provider_data=content
        ))

    def _to_gemini(self, conversation: list[Message]) -> list[types.Content]:
        contents: list[types.Content] = []
        gemini_call_ids = set()

        def add_user_part(part: types.Part):
            if contents and contents[-1].role == "user":
                contents[-1].parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))

        for message in conversation:
            if message.role == "tool":
                # Only echo ids that Gemini itself issued
                call_id = message.tool_call_id if message.tool_call_id in gemini_call_ids else None
                add_user_part(types.Part(function_response=types.FunctionResponse(
                    id=call_id, name=message.tool_name, response={"result": message.content}
                )))

            elif message.role == "assistant":
                if message.provider == self.name and message.provider_data is not None:
                    contents.append(message.provider_data)
                    gemini_call_ids.update(
                        tc.id for tc in message.tool_calls if not tc.id.startswith(SYNTHETIC_ID_PREFIX)
                    )
                    continue

                # A turn produced by another provider, rebuilt without thought signatures
                parts = []
                if message.content:
                    parts.append(types.Part(text=message.content))
                for tc in message.tool_calls:
                    parts.append(types.Part(function_call=types.FunctionCall(name=tc.name, args=tc.arguments)))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))

            else:
                add_user_part(types.Part(text=message.content))

        if not contents or contents[0].role != "user":
            contents.insert(0, types.Content(role="user", parts=[types.Part(text=BOOT_PROMPT)]))

        return contents
