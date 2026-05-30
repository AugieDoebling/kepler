from asyncio import selector_events
import threading

class HexarthState:
    def __init__(self):
        self._lock = threading.Lock()
        self.queued_actions = []

    def queue_action(self, command: str, args: dict, duration_ms: int):
        with self._lock:
            self.queued_actions.append({"command": command, "args": args, "duration_ms": duration_ms})
        
    def pop_action(self):
        """Get and remove the first queued action"""
        with self._lock:
            if len(self.queued_actions) > 0:
                return self.queued_actions.pop(0)
            return None

    def clear_actions(self):
        """Clear all queued actions"""
        with self._lock:
            self.queued_actions = []
        