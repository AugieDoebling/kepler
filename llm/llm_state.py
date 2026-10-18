import logging
import os
import threading
import time
from .llm_types import Message

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.md")

def load_system_prompt(path: str = SYSTEM_PROMPT_PATH) -> Message:
    """
    Read the system prompt file, the whole file becomes one system message.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"System prompt file not found: {path}")

    with open(path, "r") as f:
        content = f.read().strip()
    logging.info("Loaded the system prompt from %s, %d characters", path, len(content))
    return Message(role="system", content=content)

class LlmState:
    def __init__(self):
        system_messages = [load_system_prompt()]
        self._lock = threading.Lock()
        self.system_messages = system_messages
        self.current_messages = system_messages
        self.awaiting_response = True
        # When the newest message was added, from time.monotonic()
        self.last_message_at = time.monotonic()

    def add_message(self, message: Message, require_response: bool):
        """
        Add a message to the current messages.
        """
        with self._lock:
            # TODO: Maintain a rolling context window
            self.current_messages.append(message)
            self.awaiting_response = require_response
            self.last_message_at = time.monotonic()

    def add_message_content(self, role: str, content: str, require_response: bool):
        self.add_message(Message(role=role, content=content), require_response)

    def add_tool_result(self, tool_call_id: str, tool_name: str, content: str, require_response: bool):
        self.add_message(
            Message(role="tool", content=content, tool_call_id=tool_call_id, tool_name=tool_name),
            require_response,
        )

    def set_awaiting_response(self, awaiting_response: bool):
        with self._lock:
            self.awaiting_response = awaiting_response

    def get_status_and_messages(self):
        with self._lock:
            response = self.awaiting_response, self.current_messages
            self.awaiting_response = False
            return response

    def get_messages_since(self, index: int) -> tuple[list[Message], int]:
        """
        A copy of the messages from index onwards, and the index to pass next time to get only newer ones.
        """
        # TODO: When the rolling context window drops old messages, indexes into the list will shift
        with self._lock:
            return list(self.current_messages[index:]), len(self.current_messages)
