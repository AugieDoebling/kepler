import threading

class DisplayState:
    def __init__(self):
        self.is_loading = False
        self.at_attention = False
        self._lock = threading.Lock()

    def set_attention(self, attention: bool):
        with self._lock:
            self.at_attention = attention
        
    def set_loading(self, loading: bool):
        with self._lock:
            self.is_loading = loading
        
    