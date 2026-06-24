import threading
from ollama import Message

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

    # def add_message(self, role: str, content: str, require_response: bool):
    #     self.add_message(Message(role=role, content=content), require_response)


    def get_status_and_messages(self):
        with self._lock:
            response = self.awaiting_response, self.current_messages
            self.awaiting_response = False
            return response
        
        