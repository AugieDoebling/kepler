"""
Tests for the actions the LLM can call. Run from the repo root with:

    pytest llm
"""
from llm import actions


def test_remember_stores_the_fact(monkeypatch):
    stored = []
    monkeypatch.setattr(actions.memory_storage, "store_memory", stored.append)
    # Actions() connects to hardware and web services, the remember action needs none of them
    assert actions.Actions.remember(None, "Sam's dentist appointment is on Friday at 3pm") == "Remembered."
    assert stored == ["Sam's dentist appointment is on Friday at 3pm"]
