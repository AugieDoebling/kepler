import threading

class OutputState:
    def __init__(self):
        self._lock = threading.Lock()
        self.output_queue = []

    def queue_output(self, text: str):
        with self._lock:
            self.output_queue.append(text)
    
    def pop_output(self):
        with self._lock:
            if len(self.output_queue) > 0:
                return self.output_queue.pop(0)
            return None

    def has_queued_output(self):
        return len(self.output_queue) > 0
        
    
    