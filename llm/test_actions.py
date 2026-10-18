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


def test_recall_returns_the_memories(monkeypatch):
   queries = []
   def fake_recall(query):
      queries.append(query)
      return ["Sam's dentist appointment is on Friday at 3pm", "Sam is nervous about dentists"]
   monkeypatch.setattr(actions.memory_storage, "recall", fake_recall)
   result = actions.Actions.recall(None, "Sam's dentist")
   assert queries == ["Sam's dentist"]
   assert result == "Sam's dentist appointment is on Friday at 3pm\nSam is nervous about dentists"


def test_recall_says_when_nothing_is_remembered(monkeypatch):
   monkeypatch.setattr(actions.memory_storage, "recall", lambda query: [])
   assert actions.Actions.recall(None, "the moon landing") == "Nothing remembered about that."
