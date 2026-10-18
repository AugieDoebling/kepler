import json
import logging
import re
import threading
import time
from datetime import date
from pathlib import Path

from llm.llm_provider import LlmProvider
from llm.llm_state import LlmState
from llm.llm_types import LlmError, Message
from memory import memory_storage

PROMPT_PATH = Path(__file__).with_name("extraction_prompt.md")

# How often to check whether a batch of conversation is ready to be read for memories
CHECK_INTERVAL_SECONDS = 5
# A batch is read once this many people's messages have built up, so a long conversation isn't held back
BATCH_USER_MESSAGES = 10
# Or once the conversation has gone quiet for this long
IDLE_SECONDS = 180
# How many existing memories to look up for each message, and in total, so the extractor can update rather than repeat
RELATED_PER_MESSAGE = 3
MAX_RELATED = 15
# Waits between retries when the provider can't be reached, the last one repeats
RETRY_DELAYS_SECONDS = (30, 60, 120, 300)
# Long enough for one request to finish, short enough not to hold up shutting down
FINAL_BATCH_TIMEOUT_SECONDS = 15.0

_stop_requested = threading.Event()
_memory_thread = None


def start_thread(llm_state: LlmState, provider: LlmProvider):
    """
    Create a thread that reads the conversation in batches and saves what is worth remembering.
    """
    global _memory_thread
    _stop_requested.clear()
    _memory_thread = threading.Thread(target=loop, args=(llm_state, provider), name="memory")
    _memory_thread.start()


def stop():
    """
    End the memory thread, which reads whatever conversation is left on its way out. Waits for that, but not forever.
    """
    _stop_requested.set()
    if _memory_thread:
        _memory_thread.join(FINAL_BATCH_TIMEOUT_SECONDS)
        if _memory_thread.is_alive():
            logging.warning("Memory thread did not finish within %.0fs, the last of the conversation was not remembered",
                            FINAL_BATCH_TIMEOUT_SECONDS)


def loop(llm_state: LlmState, provider: LlmProvider):
    logging.info("Starting memory thread with provider %s", provider.name)
    try:
        memory_storage.warm_up()
    except Exception:
        logging.exception("Could not load memory storage, nothing will be remembered")
        return

    prompt = PROMPT_PATH.read_text().strip()
    # Index into the conversation of the first message not yet read for memories
    read_up_to = 0
    failures = 0
    retry_at = 0.0

    while not _stop_requested.wait(CHECK_INTERVAL_SECONDS):
        now = time.monotonic()
        if now < retry_at:
            continue
        messages, end = llm_state.get_messages_since(read_up_to)
        if not batch_due(messages, llm_state.last_message_at, now):
            continue

        if read_batch(provider, prompt, messages):
            read_up_to = end
            failures = 0
        else:
            delay = RETRY_DELAYS_SECONDS[min(failures, len(RETRY_DELAYS_SECONDS) - 1)]
            failures += 1
            retry_at = time.monotonic() + delay
            logging.info("Will try reading the conversation for memories again in %ds", delay)

    messages, _ = llm_state.get_messages_since(read_up_to)
    if count_user_messages(messages):
        logging.info("Reading the rest of the conversation for memories before stopping")
        read_batch(provider, prompt, messages)
    logging.info("Memory thread stopped")


def count_user_messages(messages: list[Message]) -> int:
    return sum(1 for message in messages if message.role == "user" and message.content.strip())


def batch_due(messages: list[Message], last_message_at: float, now: float) -> bool:
    """
    Whether enough has been said, or the conversation has been quiet for long enough, to read it for memories.
    """
    user_messages = count_user_messages(messages)
    if user_messages == 0:
        return False
    return user_messages >= BATCH_USER_MESSAGES or now - last_message_at >= IDLE_SECONDS


def build_transcript(messages: list[Message]) -> str:
    """
    The spoken conversation as text, leaving out the system prompt, tool calls and tool results.
    """
    lines = []
    for message in messages:
        content = message.content.strip()
        if not content:
            continue
        if message.role == "user":
            lines.append(f"Person: {content}")
        elif message.role == "assistant":
            lines.append(f"Kepler: {content}")
    return "\n".join(lines)


def find_related_memories(messages: list[Message]) -> dict[int, str]:
    """
    Memories that relate to what people said, so the extractor can see what is already known.
    """
    related = {}
    for message in messages:
        if message.role != "user" or not message.content.strip():
            continue
        for memory_id, content in memory_storage.recall_with_ids(message.content, RELATED_PER_MESSAGE, mark_used=False):
            related[memory_id] = content
            if len(related) >= MAX_RELATED:
                return related
    return related


def build_request(prompt: str, related: dict[int, str], transcript: str, today: date) -> list[Message]:
    if related:
        known = "\n".join(f"[{memory_id}] {content}" for memory_id, content in related.items())
    else:
        known = "None"
    body = (
        f"Today is {today.strftime('%A %d %B %Y')}.\n\n"
        f"Memories Kepler already has:\n{known}\n\n"
        f"Conversation:\n{transcript}"
    )
    return [Message(role="system", content=prompt), Message(role="user", content=body)]


def parse_changes(reply: str) -> dict | None:
    """
    Read the extractor's JSON reply, allowing for it being wrapped in a code block. None if it isn't usable.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", reply, re.DOTALL)
    text = fenced.group(1) if fenced else reply
    try:
        changes = json.loads(text.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(changes, dict):
        return None

    def is_id(value):
        # JSON true and false would otherwise pass as the ids 1 and 0
        return isinstance(value, int) and not isinstance(value, bool)

    def items(key):
        value = changes.get(key, [])
        return value if isinstance(value, list) else []

    return {
        "add": [content for content in items("add") if isinstance(content, str) and content.strip()],
        "update": [
            {"id": change["id"], "content": change["content"]}
            for change in items("update")
            if isinstance(change, dict) and is_id(change.get("id"))
            and isinstance(change.get("content"), str) and change["content"].strip()
        ],
        "forget": [memory_id for memory_id in items("forget") if is_id(memory_id)],
    }


def apply_changes(changes: dict, related: dict[int, str]):
    """
    Save the extractor's changes. It may only update or forget memories it was shown.
    """
    for memory_id in changes["forget"]:
        if memory_id not in related:
            logging.warning("Extractor asked to forget memory %d, which it was not shown, ignoring it", memory_id)
            continue
        memory_storage.forget_memory(memory_id)

    for change in changes["update"]:
        if change["id"] not in related:
            logging.warning("Extractor asked to update memory %d, which it was not shown, ignoring it", change["id"])
            continue
        memory_storage.update_memory(change["id"], change["content"])

    for content in changes["add"]:
        memory_storage.store_memory(content)


def read_batch(provider: LlmProvider, prompt: str, messages: list[Message]) -> bool:
    """
    Read one batch of conversation for memories and save them.
    Returns False when the batch should be tried again later because the provider couldn't be reached.
    """
    transcript = build_transcript(messages)
    if not transcript:
        return True

    started = time.perf_counter()
    try:
        related = find_related_memories(messages)
        response = provider.chat(build_request(prompt, related, transcript, date.today()), [])
    except LlmError as e:
        logging.error("Could not read the conversation for memories (%s): %s", type(e).__name__, e)
        return False
    except Exception:
        # Retrying would most likely fail the same way, so the batch is skipped rather than retried forever
        logging.exception("Reading the conversation for memories failed, skipping %d messages", len(messages))
        return True

    reply = response.message.content
    changes = parse_changes(reply)
    if changes is None:
        logging.error("Memory extractor reply was not the JSON expected, skipping %d messages: %r", len(messages), reply)
        return True

    logging.info("Memory extractor read %d messages in %.1fs: %d to add, %d to update, %d to forget",
                 len(messages), time.perf_counter() - started,
                 len(changes["add"]), len(changes["update"]), len(changes["forget"]))
    try:
        apply_changes(changes, related)
    except Exception:
        logging.exception("Saving memories failed partway through")
    return True
