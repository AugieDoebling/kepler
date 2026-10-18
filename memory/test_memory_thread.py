"""
Tests for memory_thread. Run from the repo root with:

    pytest memory

Storage is replaced with a fake that records what it is asked to do, and the provider with one that replies
with whatever the test sets, so these test reading conversations for memories without any models or network.
"""
import threading
from datetime import date

import pytest

from llm.llm_state import LlmState
from llm.llm_types import LlmResponse, LlmUnavailableError, Message, ToolCall
from memory import memory_thread


class FakeStorage:
    def __init__(self):
        self.memories = {}
        self.added = []
        self.updated = []
        self.forgotten = []
        self.recall_calls = []

    def recall_with_ids(self, query, limit=5, mark_used=True):
        self.recall_calls.append((query, limit, mark_used))
        words = set(query.lower().split())
        return [(memory_id, content) for memory_id, content in self.memories.items()
                if words & set(content.lower().split())][:limit]

    def store_memory(self, content):
        self.added.append(content)

    def update_memory(self, memory_id, content):
        self.updated.append((memory_id, content))

    def forget_memory(self, memory_id):
        self.forgotten.append(memory_id)

    def warm_up(self):
        pass


class FakeProvider:
    name = "fake"

    def __init__(self, reply='{"add": [], "update": [], "forget": []}'):
        self.reply = reply
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append((messages, tools))
        if isinstance(self.reply, Exception):
            raise self.reply
        return LlmResponse(message=Message(role="assistant", content=self.reply))


@pytest.fixture
def storage(monkeypatch):
    fake = FakeStorage()
    for name in ("recall_with_ids", "store_memory", "update_memory", "forget_memory", "warm_up"):
        monkeypatch.setattr(memory_thread.memory_storage, name, getattr(fake, name))
    return fake


def user(content):
    return Message(role="user", content=content)


def kepler(content):
    return Message(role="assistant", content=content)


# When a batch is due

def test_batch_not_due_without_user_messages():
    assert not memory_thread.batch_due([kepler("Good morning")], last_message_at=0, now=10_000)


def test_batch_not_due_while_conversation_is_active():
    assert not memory_thread.batch_due([user("hi")], last_message_at=100, now=100 + memory_thread.IDLE_SECONDS - 1)


def test_batch_due_once_conversation_goes_quiet():
    assert memory_thread.batch_due([user("hi")], last_message_at=100, now=100 + memory_thread.IDLE_SECONDS)


def test_batch_due_once_enough_user_messages_build_up():
    messages = [user(f"message {index}") for index in range(memory_thread.BATCH_USER_MESSAGES)]
    assert memory_thread.batch_due(messages, last_message_at=100, now=101)


def test_empty_user_messages_do_not_count_towards_a_batch():
    messages = [user("  ") for _ in range(memory_thread.BATCH_USER_MESSAGES)]
    assert not memory_thread.batch_due(messages, last_message_at=0, now=10_000)


# Building the request

def test_transcript_keeps_only_what_was_said():
    messages = [
        Message(role="system", content="You are Kepler"),
        user("I'm allergic to peanuts"),
        Message(role="assistant", content="", tool_calls=[ToolCall(id="1", name="dance", arguments={})]),
        Message(role="tool", content="ok", tool_call_id="1", tool_name="dance"),
        kepler("Noted, no peanuts."),
        user("  "),
    ]
    assert memory_thread.build_transcript(messages) == "Person: I'm allergic to peanuts\nKepler: Noted, no peanuts."


def test_request_includes_date_memories_and_conversation():
    request = memory_thread.build_request("PROMPT", {12: "Augie loves ramen"}, "Person: hi", date(2026, 10, 17))
    assert request[0] == Message(role="system", content="PROMPT")
    assert request[1].role == "user"
    assert "Saturday 17 October 2026" in request[1].content
    assert "[12] Augie loves ramen" in request[1].content
    assert request[1].content.endswith("Conversation:\nPerson: hi")


def test_request_says_when_there_are_no_memories():
    request = memory_thread.build_request("PROMPT", {}, "Person: hi", date(2026, 10, 17))
    assert "Memories Kepler already has:\nNone" in request[1].content


def test_related_memories_are_looked_up_for_user_messages_only(storage):
    storage.memories = {1: "Augie loves ramen", 2: "The dog is named Biscuit"}
    related = memory_thread.find_related_memories([kepler("ramen Biscuit"), user("I love ramen")])
    assert related == {1: "Augie loves ramen"}
    assert storage.recall_calls == [("I love ramen", memory_thread.RELATED_PER_MESSAGE, False)]


def test_related_memories_are_capped(storage, monkeypatch):
    monkeypatch.setattr(memory_thread, "MAX_RELATED", 2)
    storage.memories = {index: f"ramen fact {index}" for index in range(10)}
    related = memory_thread.find_related_memories([user("ramen"), user("ramen again")])
    assert len(related) == 2


# Reading the reply

def test_parses_plain_json():
    assert memory_thread.parse_changes('{"add": ["A"], "update": [{"id": 1, "content": "B"}], "forget": [2]}') == {
        "add": ["A"], "update": [{"id": 1, "content": "B"}], "forget": [2],
    }


def test_parses_json_in_a_code_block():
    reply = 'Here you go:\n```json\n{"add": ["A"], "update": [], "forget": []}\n```'
    assert memory_thread.parse_changes(reply)["add"] == ["A"]


@pytest.mark.parametrize("reply", ["not json", "[1, 2]", '"just a string"', "", "```json\n{broken\n```"])
def test_unusable_reply_gives_none(reply):
    assert memory_thread.parse_changes(reply) is None


def test_missing_lists_count_as_empty():
    assert memory_thread.parse_changes('{"add": ["A"]}') == {"add": ["A"], "update": [], "forget": []}


def test_malformed_items_are_dropped():
    reply = """{
        "add": ["A", "", 3, null],
        "update": [{"id": 1, "content": "B"}, {"id": "1", "content": "C"}, {"id": 2}, {"id": 3, "content": " "}, {"id": true, "content": "D"}, "x"],
        "forget": [4, "5", null, true],
        "extra": "ignored"
    }"""
    assert memory_thread.parse_changes(reply) == {"add": ["A"], "update": [{"id": 1, "content": "B"}], "forget": [4]}


def test_lists_of_the_wrong_type_count_as_empty():
    assert memory_thread.parse_changes('{"add": "A", "update": {}, "forget": 3}') == {"add": [], "update": [], "forget": []}


# Saving the changes

def test_changes_are_saved(storage):
    changes = {"add": ["New fact"], "update": [{"id": 1, "content": "Changed fact"}], "forget": [2]}
    memory_thread.apply_changes(changes, related={1: "Old fact", 2: "Wrong fact"})
    assert storage.added == ["New fact"]
    assert storage.updated == [(1, "Changed fact")]
    assert storage.forgotten == [2]


def test_memories_not_shown_to_the_extractor_are_left_alone(storage):
    changes = {"add": [], "update": [{"id": 7, "content": "Changed"}], "forget": [8]}
    memory_thread.apply_changes(changes, related={1: "Shown fact"})
    assert storage.updated == []
    assert storage.forgotten == []


# Reading a batch

def test_batch_saves_what_the_extractor_finds(storage):
    storage.memories = {1: "Augie loves ramen"}
    provider = FakeProvider('{"add": ["Augie is allergic to peanuts"], "update": [], "forget": []}')
    assert memory_thread.read_batch(provider, "PROMPT", [user("I'm allergic to peanuts, I love ramen")])
    assert storage.added == ["Augie is allergic to peanuts"]

    messages, tools = provider.requests[0]
    assert tools == []
    assert "[1] Augie loves ramen" in messages[1].content
    assert "Person: I'm allergic to peanuts, I love ramen" in messages[1].content


def test_batch_is_kept_for_retry_when_provider_is_unavailable(storage):
    provider = FakeProvider(LlmUnavailableError("offline"))
    assert memory_thread.read_batch(provider, "PROMPT", [user("I'm allergic to peanuts")]) is False
    assert storage.added == []


def test_batch_is_skipped_when_reply_is_unusable(storage):
    assert memory_thread.read_batch(FakeProvider("Sorry, I can't help with that"), "PROMPT", [user("hi")]) is True
    assert storage.added == []


def test_batch_with_nothing_said_does_not_call_provider(storage):
    provider = FakeProvider()
    assert memory_thread.read_batch(provider, "PROMPT", [kepler(""), user("  ")]) is True
    assert provider.requests == []


def test_batch_is_skipped_when_something_unexpected_fails(storage, monkeypatch):
    def broken_recall(*args, **kwargs):
        raise RuntimeError("database is broken")

    monkeypatch.setattr(memory_thread.memory_storage, "recall_with_ids", broken_recall)
    assert memory_thread.read_batch(FakeProvider(), "PROMPT", [user("hi")]) is True


# The thread

@pytest.fixture
def stopped(monkeypatch):
    """
    Make the loop see a stop request straight away, so it goes straight to its final batch.
    """
    stop_requested = threading.Event()
    stop_requested.set()
    monkeypatch.setattr(memory_thread, "_stop_requested", stop_requested)


def test_reads_the_rest_of_the_conversation_when_stopping(storage, stopped):
    llm_state = LlmState()
    llm_state.add_message_content("user", "My name is Sam", require_response=True)
    provider = FakeProvider('{"add": ["Someone in the household is named Sam"], "update": [], "forget": []}')
    memory_thread.loop(llm_state, provider)
    assert storage.added == ["Someone in the household is named Sam"]


def test_nothing_to_read_when_stopping_skips_the_provider(storage, stopped):
    provider = FakeProvider()
    memory_thread.loop(LlmState(), provider)
    assert provider.requests == []


def test_stops_without_reading_when_storage_cannot_load(storage, stopped, monkeypatch):
    def broken_warm_up():
        raise RuntimeError("model download failed")

    monkeypatch.setattr(memory_thread.memory_storage, "warm_up", broken_warm_up)
    llm_state = LlmState()
    llm_state.add_message_content("user", "My name is Sam", require_response=True)
    provider = FakeProvider()
    memory_thread.loop(llm_state, provider)
    assert provider.requests == []
