import threading

class HexarthState:
    def __init__(self):
        self._lock = threading.Lock()
        self.queued_actions = []

    def queue_action(self, command: str, args: dict, duration_ms: int):
        """
        Queue an action for the robot.
        
        :param command: The name of the command to queue.
        :param args: The arguments for the command.
        :param duration_ms: The duration of the command in milliseconds.
        """
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
        