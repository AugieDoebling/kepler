import threading
from .llm_types import Message

class LlmState:
    def __init__(self, system_messages):
        self._lock = threading.Lock()
        self.system_messages = system_messages
        self.current_messages = system_messages
        self.awaiting_response = True

    def add_message(self, message: Message, require_response: bool):
        """
        Add a message to the current messages.
        """
        with self._lock:
            # TODO: Maintain a rolling context window
            self.current_messages.append(message)
            self.awaiting_response = require_response

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
