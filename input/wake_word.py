"""Decide whether a transcribed line was addressed to the robot.

Speech to text runs all the time, so the wake word is matched against the
transcript instead of using a separate wake word model:

    wake_word = WakeWordFilter("Kepler")
    wake_word.filter("Kepler, what time is it?")   # -> "Kepler, what time is it?"
    wake_word.filter("What's on the telly?")       # -> None

Saying only the wake word opens a short window in which the next line is
accepted without it, for "Kepler ... <pause> ... what time is it?".
"""
import difflib
import re
import time
from typing import Optional

DEFAULT_WAKE_WORD = "Kepler"
DEFAULT_WINDOW_SECONDS = 6.0

# How close a heard word has to be to the wake word, so "Keppler" and "Kepler's" still count
MATCH_THRESHOLD = 0.75


class WakeWordFilter:
    def __init__(self, wake_word: str = DEFAULT_WAKE_WORD, window_seconds: float = DEFAULT_WINDOW_SECONDS):
        # An empty wake word turns the filter off, so every line is accepted
        self.wake_word = wake_word.strip().lower()
        self.window_seconds = window_seconds
        self._awake_until = 0.0

    @classmethod
    def from_config(cls, config: dict) -> "WakeWordFilter":
        listening_config = config.get("listening", {})
        return cls(
            wake_word=listening_config.get("wake_word", DEFAULT_WAKE_WORD),
            window_seconds=listening_config.get("wake_word_window_seconds", DEFAULT_WINDOW_SECONDS),
        )

    def matches(self, text: str, now: Optional[float] = None) -> bool:
        """
        True if the text, which may still be being spoken, looks addressed to the robot. Changes nothing.
        """
        if not self.wake_word:
            return bool(text.strip())
        if now is None:
            now = time.monotonic()
        return now < self._awake_until or any(self._is_wake_word(word) for word in self._words(text))

    def filter(self, text: str, now: Optional[float] = None) -> Optional[str]:
        """
        Return the text if it should go to the LLM, or None if it should be ignored.
        """
        text = text.strip()
        if not text:
            return None
        if not self.wake_word:
            return text
        if now is None:
            now = time.monotonic()

        matches = [self._is_wake_word(word) for word in self._words(text)]

        if any(matches):
            if all(matches):
                # Only the wake word was said, so wait for what comes next
                self._awake_until = now + self.window_seconds
                return None
            self._awake_until = 0.0
            return text

        if now < self._awake_until:
            self._awake_until = 0.0
            return text

        return None

    @staticmethod
    def _words(text: str) -> list:
        return re.findall(r"[a-z']+", text.lower())

    def _is_wake_word(self, word: str) -> bool:
        word = word.strip("'")
        if word.endswith("'s"):
            word = word[:-2]
        return difflib.SequenceMatcher(None, word, self.wake_word).ratio() >= MATCH_THRESHOLD
