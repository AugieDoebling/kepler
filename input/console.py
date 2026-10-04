"""Shows a spoken line on the console while it is being said, with the keyboard paused.

    console = SpeechConsole()
    console.show("Kepler, what")           # --> Kepler, what
    console.show("Kepler, what time is")   # the same console line is rewritten
    console.finish("Kepler, what time is it?")

While a line is on screen, typed keys are neither shown nor submitted, so they
cannot garble it. Anything typed in that time is thrown away.
"""
import shutil
import sys
import threading

try:
    import termios
except ImportError:
    # Not available on Windows, the keyboard is then not paused
    termios = None

PROMPT = "--> "
CLEAR_LINE = "\r\033[K"


class SpeechConsole:
    def __init__(self):
        self._lock = threading.Lock()
        self._active = False
        self._saved_terminal = None

    @property
    def active(self) -> bool:
        """True while a spoken line is on screen and the keyboard is paused."""
        return self._active

    def show(self, text: str):
        """
        Show the line as heard so far, replacing what was shown before.
        """
        with self._lock:
            if not self._active:
                self._active = True
                self._pause_keyboard()

            # Rewriting only works within one row of the terminal, so a long line shows its end
            room = shutil.get_terminal_size().columns - len(PROMPT) - 1
            if len(text) > room:
                text = "…" + text[-(room - 1):]
            sys.stdout.write(CLEAR_LINE + PROMPT + text)
            sys.stdout.flush()

    def finish(self, text: str):
        """
        Print the completed line in full and hand the console back to the keyboard.
        """
        with self._lock:
            sys.stdout.write((CLEAR_LINE if self._active else "") + PROMPT + text + "\n")
            sys.stdout.flush()
            self._release()

    def cancel(self):
        """
        Remove a line that turned out not to be addressed to the robot.
        """
        with self._lock:
            if self._active:
                sys.stdout.write(CLEAR_LINE)
                sys.stdout.flush()
            self._release()

    def _release(self):
        if self._active:
            self._resume_keyboard()
            self._active = False

    def _pause_keyboard(self):
        if termios is None or not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._saved_terminal = termios.tcgetattr(fd)
        quiet = termios.tcgetattr(fd)
        quiet[3] &= ~termios.ECHO   # index 3 holds the local flags
        termios.tcsetattr(fd, termios.TCSANOW, quiet)

    def _resume_keyboard(self):
        if self._saved_terminal is None:
            return
        fd = sys.stdin.fileno()
        # Throw away what was typed while paused, including anything half typed before the pause
        termios.tcflush(fd, termios.TCIFLUSH)
        termios.tcsetattr(fd, termios.TCSANOW, self._saved_terminal)
        self._saved_terminal = None
