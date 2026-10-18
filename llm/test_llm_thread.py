"""
Tests for adding recalled memories to LLM requests. Run from the repo root with:

    pytest llm

Memory storage, the provider and the actions are fakes, so the LLM loop runs without any models or network.
The fake provider stops the otherwise endless loop by raising StopLoop.
"""
import pytest

from llm import llm_thread
from llm.llm_state import LlmState
from llm.llm_types import LlmResponse, Message, ToolCall


class StopLoop(BaseException):
    pass


class FakeProvider:
    name = "fake"

    def __init__(self, replies):
        # Each reply is a Message to return, once they run out the loop is stopped
        self.replies = list(replies)
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append(list(messages))
        if not self.replies:
            raise StopLoop()
        return LlmResponse(message=self.replies.pop(0))


class FakeActions:
    def __init__(self):
        self.calls = []

    def get_actions(self):
        return []

    def call_action(self, name, arguments):
        self.calls.append((name, arguments))
        return "ok"


@pytest.fixture
def recalls(monkeypatch):
    """
    Every query recall is asked, it remembers one fact about the dentist.
    """
    queries = []
    def fake_recall(query):
        queries.append(query)
        return ["Sam's dentist appointment is on Friday at 3pm"] if "dentist" in query else []
    monkeypatch.setattr(llm_thread.memory_storage, "recall", fake_recall)
    return queries


def conversation(user_says):
    state = LlmState()
    state.add_message_content("assistant", "Good morning.", require_response=False)
    state.add_message_content("user", user_says, require_response=True)
    return state


def run(state, provider, auto_recall=True):
    with pytest.raises(StopLoop):
        llm_thread.loop(FakeActions(), state, provider, auto_recall=auto_recall)


def test_memories_are_added_to_the_request(recalls):
    state = conversation("When is my dentist appointment?")
    provider = FakeProvider([])
    run(state, provider)

    assert recalls == ["When is my dentist appointment?"]
    sent = provider.requests[0][-1]
    assert sent.role == "user"
    assert sent.content.startswith("When is my dentist appointment?")
    assert "Sam's dentist appointment is on Friday at 3pm" in sent.content


def test_memories_are_not_kept_in_the_conversation(recalls):
    state = conversation("When is my dentist appointment?")
    run(state, FakeProvider([]))
    assert state.current_messages[-1].content == "When is my dentist appointment?"


def test_nothing_added_when_nothing_is_remembered(recalls):
    state = conversation("What is the biggest moon of Saturn?")
    provider = FakeProvider([])
    run(state, provider)
    assert provider.requests[0][-1].content == "What is the biggest moon of Saturn?"


def test_no_recall_when_turned_off(recalls):
    state = conversation("When is my dentist appointment?")
    provider = FakeProvider([])
    run(state, provider, auto_recall=False)
    assert recalls == []
    assert provider.requests[0][-1].content == "When is my dentist appointment?"


def test_no_recall_before_anyone_speaks(recalls):
    state = LlmState()
    run(state, FakeProvider([]))
    assert recalls == []


def test_recalled_once_across_tool_rounds(recalls):
    state = conversation("When is my dentist appointment?")
    tool_call = ToolCall(id="1", name="move_head", arguments={"pan_degrees": 0, "tilt_degrees": -20, "speed": 30})
    provider = FakeProvider([Message(role="assistant", tool_calls=[tool_call])])
    run(state, provider)

    assert recalls == ["When is my dentist appointment?"]
    # The second request comes after the tool result, the memories stay with the user's message
    assert len(provider.requests) == 2
    assert provider.requests[1][-1].role == "tool"
    assert "Friday at 3pm" in provider.requests[1][-3].content


def test_a_failing_recall_does_not_stop_the_request(monkeypatch):
    def broken_recall(query):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(llm_thread.memory_storage, "recall", broken_recall)
    state = conversation("When is my dentist appointment?")
    provider = FakeProvider([])
    run(state, provider)
    assert provider.requests[0][-1].content == "When is my dentist appointment?"
