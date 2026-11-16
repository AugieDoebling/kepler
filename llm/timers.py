import itertools
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

# A day is plenty for a kitchen timer or a reminder, and stops a typo turning into a timer for years
MAX_TIMER_MINUTES = 24 * 60
TIME_FORMATS = ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p")


def parse_clock_time(text: str, now: datetime) -> datetime:
    """The next time the clock shows text, such as "15:30" or "3:30 pm", today or else tomorrow."""
    cleaned = text.strip().upper().replace(".", "")
    for time_format in TIME_FORMATS:
        try:
            clock = datetime.strptime(cleaned, time_format).time()
        except ValueError:
            continue
        due = datetime.combine(now.date(), clock)
        return due if due > now else due + timedelta(days=1)
    raise ValueError(f"Can't read {text!r} as a time, use a form like \"15:30\" or \"3:30 PM\".")


class Timers:
    """
    Timers and reminders the LLM sets. When one is due, deliver is called with a note for the LLM, which is
    queued like something the user said so the robot speaks up on its own.
    They are kept in memory only, so a restart loses them.
    """

    def __init__(self, deliver: Callable[[str], None], clock: Callable[[], datetime] = datetime.now):
        self.deliver = deliver
        self.clock = clock
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        # id -> (due time, reminder, threading.Timer)
        self._timers: dict[int, tuple[datetime, str, threading.Timer]] = {}

    def timer(self, action: str, reminder: Optional[str] = None, minutes: Optional[float] = None, at: Optional[str] = None,
              timer_id: Optional[int] = None) -> str:
        """
        Set, list or cancel timers and reminders. When a timer goes off you will be told, so you can tell the user.

        :param action: "set" to start a timer, "list" to see the ones running, or "cancel" to stop one.
        :param reminder: For "set", what the timer is for, such as "take the pasta off the stove".
        :param minutes: For "set", how many minutes from now it goes off. Give this or at, not both.
        :param at: For "set", the clock time it goes off, such as "15:30" or "3:30 PM". Give this or minutes, not both.
        :param timer_id: For "cancel", the number of the timer, from "list". Leave it out to cancel the only one running.
        """
        action = (action or "").strip().lower()
        if action == "set":
            return self.set(reminder, minutes, at)
        if action == "list":
            return self.list()
        if action == "cancel":
            return self.cancel(timer_id)
        return f"Error: unknown action {action!r}, use set, list or cancel."

    def set(self, reminder: Optional[str], minutes: Optional[float] = None, at: Optional[str] = None) -> str:
        now = self.clock()
        reminder = (reminder or "").strip() or "a timer"
        if at:
            try:
                due = parse_clock_time(at, now)
            except ValueError as e:
                return f"Error: {e}"
        elif minutes is not None:
            minutes = float(minutes)
            if not 0 < minutes <= MAX_TIMER_MINUTES:
                return f"Error: minutes must be more than 0 and at most {MAX_TIMER_MINUTES}."
            due = now + timedelta(minutes=minutes)
        else:
            return "Error: give either minutes or at."

        with self._lock:
            timer_id = next(self._ids)
            thread_timer = threading.Timer((due - now).total_seconds(), self._fire, args=(timer_id,))
            thread_timer.daemon = True
            thread_timer.name = f"timer-{timer_id}"
            self._timers[timer_id] = (due, reminder, thread_timer)
            thread_timer.start()
        logging.info("Set timer %d for %s: %s", timer_id, due.isoformat(timespec="seconds"), reminder)
        return f"Timer {timer_id} set for {self._describe_due(due, now)}: {reminder}."

    def list(self) -> str:
        now = self.clock()
        with self._lock:
            running = sorted(self._timers.items(), key=lambda item: item[1][0])
        if not running:
            return "No timers are running."
        return "\n".join(f"Timer {timer_id}: {reminder}, {self._describe_due(due, now)}"
                         for timer_id, (due, reminder, _) in running)

    def cancel(self, timer_id: Optional[int] = None) -> str:
        with self._lock:
            if timer_id is None:
                if len(self._timers) != 1:
                    return "No timers are running." if not self._timers else \
                        "Error: more than one timer is running, say which with timer_id. " + self._list_locked()
                timer_id = next(iter(self._timers))
            entry = self._timers.pop(int(timer_id), None)
        if entry is None:
            return f"Error: there is no timer {timer_id}."
        entry[2].cancel()
        logging.info("Cancelled timer %d: %s", timer_id, entry[1])
        return f"Cancelled timer {timer_id}: {entry[1]}."

    def cancel_all(self):
        with self._lock:
            entries, self._timers = list(self._timers.values()), {}
        for _, _, thread_timer in entries:
            thread_timer.cancel()

    def _list_locked(self) -> str:
        return " ".join(f"Timer {timer_id}: {reminder}." for timer_id, (_, reminder, _) in self._timers.items())

    def _fire(self, timer_id: int):
        with self._lock:
            entry = self._timers.pop(timer_id, None)
        if entry is None:
            return
        logging.info("Timer %d went off: %s", timer_id, entry[1])
        self.deliver(f"(A timer you set has gone off: {entry[1]}. Tell the user now.)")

    @staticmethod
    def _describe_due(due: datetime, now: datetime) -> str:
        seconds = max(0, round((due - now).total_seconds()))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = [f"{hours} hour{'s' * (hours != 1)}"] * bool(hours) + [f"{minutes} minute{'s' * (minutes != 1)}"] * bool(minutes)
        if not parts:
            parts = [f"{seconds} second{'s' * (seconds != 1)}"]
        clock = due.strftime("%I:%M %p").lstrip("0")
        return f"{clock}, in {' '.join(parts)}"
