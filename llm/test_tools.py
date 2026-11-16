"""
Tests for the calculator, timers, forget and the tool schemas sent to Ollama. Run from the repo root with:

    pytest llm

Nothing here needs the network, memory storage is faked.
"""
import threading
from datetime import datetime

import pytest

from llm import actions, basic_tools, robot_status
from llm.ollama_provider import OllamaProvider
from llm.timers import Timers, parse_clock_time


@pytest.mark.parametrize("expression, expected", [
    ("18 * 0.2", "18 * 0.2 = 3.6"),
    ("2^10", "2**10 = 1024"),
    ("sqrt(16) + 1", "sqrt(16) + 1 = 5"),
    ("round(pi, 2)", "round(pi, 2) = 3.14"),
    ("10 / 4", "10 / 4 = 2.5"),
])
def test_calculate(expression, expected):
    assert basic_tools.calculate(expression) == expected


@pytest.mark.parametrize("expression", [
    "__import__('os').system('ls')",
    "open('/etc/passwd')",
    "(1).__class__",
    "9 ** 9 ** 9",
    "1 / 0",
    "2 +",
])
def test_calculate_refuses_anything_but_maths(expression):
    assert basic_tools.calculate(expression).startswith("Error")


def test_get_time_names_the_day():
    assert datetime.now().strftime("%A") in basic_tools.get_time()


def test_robot_status_reports_without_failing():
    status = robot_status.robot_status()
    assert status.startswith("Awake for")


NOW = datetime(2026, 11, 15, 21, 30)


@pytest.mark.parametrize("text, expected", [
    ("22:15", datetime(2026, 11, 15, 22, 15)),
    ("10:15 pm", datetime(2026, 11, 15, 22, 15)),
    ("9 PM", datetime(2026, 11, 16, 21, 0)),  # already past today, so tomorrow
    ("7:00 a.m.", datetime(2026, 11, 16, 7, 0)),
])
def test_parse_clock_time(text, expected):
    assert parse_clock_time(text, NOW) == expected


def test_timer_goes_off_and_is_delivered():
    delivered = []
    went_off = threading.Event()
    timers = Timers(deliver=lambda note: (delivered.append(note), went_off.set()))
    result = timers.timer("set", reminder="take the pasta off", minutes=0.001)
    assert result.startswith("Timer 1 set for")
    assert went_off.wait(2)
    assert "take the pasta off" in delivered[0]
    assert timers.timer("list") == "No timers are running."


def test_timer_list_and_cancel():
    timers = Timers(deliver=lambda note: pytest.fail("a cancelled timer went off"), clock=lambda: NOW)
    timers.timer("set", reminder="pasta", minutes=10)
    timers.timer("set", reminder="call Sam", at="10:00 PM")
    try:
        listing = timers.timer("list")
        assert "Timer 1: pasta, 9:40 PM, in 10 minutes" in listing
        assert "Timer 2: call Sam, 10:00 PM, in 30 minutes" in listing
        # With two running, which one has to be said
        assert timers.timer("cancel").startswith("Error")
        assert timers.timer("cancel", timer_id=1) == "Cancelled timer 1: pasta."
        assert timers.timer("cancel") == "Cancelled timer 2: call Sam."
        assert timers.timer("cancel", timer_id=5) == "Error: there is no timer 5."
    finally:
        timers.cancel_all()


def test_timer_needs_a_time():
    timers = Timers(deliver=print)
    assert timers.timer("set", reminder="pasta").startswith("Error")
    assert timers.timer("set", reminder="pasta", minutes=-5).startswith("Error")
    assert timers.timer("set", reminder="pasta", at="teatime").startswith("Error")
    assert timers.timer("snooze").startswith("Error")


@pytest.fixture
def memories(monkeypatch):
    stored = {1: "Sam's dentist appointment is on Friday at 3pm", 2: "Sam's dentist is Dr Lee", 3: "Augie likes tacos"}
    def fake_recall_with_ids(query, limit=5, mark_used=True):
        return [(i, c) for i, c in stored.items() if any(w in c.lower() for w in query.lower().split())]
    monkeypatch.setattr(actions.memory_storage, "recall_with_ids", fake_recall_with_ids)
    monkeypatch.setattr(actions.memory_storage, "forget_memory", lambda memory_id: stored.pop(memory_id, None) is not None)
    return stored


def test_forget_one_match(memories):
    assert actions.Actions.forget(None, "tacos") == "Forgotten: Augie likes tacos"
    assert 3 not in memories


def test_forget_asks_which_when_several_match(memories):
    result = actions.Actions.forget(None, "dentist")
    assert "[1]" in result and "[2]" in result
    assert len(memories) == 3
    assert actions.Actions.forget(None, "dentist", memory_id=2) == "Forgotten: Sam's dentist is Dr Lee"
    assert 2 not in memories


def test_forget_wont_delete_an_unrelated_id(memories):
    assert "nothing was forgotten" in actions.Actions.forget(None, "dentist", memory_id=3)
    assert 3 in memories


def test_forget_nothing_matches(memories):
    assert "nothing to forget" in actions.Actions.forget(None, "the moon")


def test_ollama_gets_the_full_schemas():
    tools = actions.Actions(None, None, None, Timers(deliver=print)).get_actions()
    converted = {spec.name: OllamaProvider._to_ollama_tool(spec)["function"] for spec in tools}
    assert converted["timer"]["parameters"]["required"] == ["action"]
    assert converted["timer"]["parameters"]["properties"]["action"]["enum"] == ["set", "list", "cancel"]
    assert converted["get_weather"]["parameters"]["required"] == []
    assert converted["move"]["parameters"]["properties"]["forward_speed"]["description"]


def test_no_timer_tool_without_timers():
    names = [spec.name for spec in actions.Actions(None, None, None).get_actions()]
    assert "timer" not in names and "forget" in names
