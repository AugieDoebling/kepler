"""
Tests for memory_storage. Run from the repo root with:

    pytest memory

Most tests swap the embedding and reranker models for fake ones so they are fast and predictable.
The real_model tests use the real models to check that search by meaning works, and are skipped if they can't load.
"""
import re
import sqlite3
import threading
import zlib

import numpy as np
import pytest
import sqlite_vec

from memory import memory_storage


def fake_embed(text: str) -> bytes:
    """
    Hash each word into a slot of the vector, so texts sharing words are close and identical texts match exactly.
    """
    vector = np.zeros(memory_storage.EMBEDDING_DIMENSIONS, dtype=np.float32)
    # Keeps the vector from being all zeros when the text has no words
    vector[0] = 0.01
    for word in re.findall(r"\w+", text.lower()):
        vector[zlib.crc32(word.encode()) % memory_storage.EMBEDDING_DIMENSIONS] += 1.0
    vector = vector / np.linalg.norm(vector)
    return sqlite_vec.serialize_float32(vector.tolist())


def fake_rerank(query: str, texts: list[str]) -> list[float]:
    """
    Score by how many search words each text shares with the query. Sharing none scores below MIN_RERANK_SCORE,
    and every extra shared word puts a text further ahead than RERANK_SCORE_GAP.
    """
    query_words = set(memory_storage._search_words(query))
    return [len(query_words & set(memory_storage._search_words(text))) * 10.0 - 9.0 for text in texts]


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """
    Give each test its own empty database file, and close the shared connection afterwards.
    """
    path = tmp_path / "test_memory.db"
    monkeypatch.setattr(memory_storage, "DB_PATH", path)
    monkeypatch.setattr(memory_storage, "_db", None)
    yield path
    if memory_storage._db is not None:
        memory_storage._db.close()


@pytest.fixture
def fake_model(db_path, monkeypatch):
    monkeypatch.setattr(memory_storage, "_embed", fake_embed)
    monkeypatch.setattr(memory_storage, "_rerank", fake_rerank)
    return db_path


@pytest.fixture
def scores(fake_model, monkeypatch):
    """
    Set the reranker score for each memory by its text, and record what was sent to be reranked.
    """
    scores_by_text = {}
    reranked = []

    def rerank(query, texts):
        reranked.append(list(texts))
        return [scores_by_text[text] for text in texts]

    monkeypatch.setattr(memory_storage, "_rerank", rerank)
    scores_by_text["reranked"] = reranked
    return scores_by_text


@pytest.fixture(scope="session")
def real_model_loaded():
    try:
        memory_storage._embed("warm up")
        memory_storage._rerank("warm up", ["warm up"])
    except Exception as error:
        pytest.skip(f"Models unavailable: {error}")


@pytest.fixture
def real_model(real_model_loaded, db_path):
    return db_path


def count(table: str) -> int:
    return memory_storage._connection().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def store_all(*contents: str) -> list[int]:
    return [memory_storage.store_memory(content) for content in contents]


def search_words(text: str) -> list[int]:
    """
    Search only the full-text index, bypassing the search by meaning.
    """
    query = memory_storage._full_text_query(memory_storage._search_words(text))
    if query is None:
        return []
    return [row[0] for row in memory_storage._connection().execute(
        "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?", (query,)
    )]


# Full-text query building

@pytest.mark.parametrize("text, expected", [
    ("Augie likes ramen", ["augie", "likes", "ramen"]),
    ("What is the dog's NAME?", ["dog", "name"]),
    ("ramen ramen Ramen", ["ramen"]),
    ("what is it", []),
    ("?!- \"\"", []),
])
def test_search_words_drops_stopwords_and_repeats(text, expected):
    assert memory_storage._search_words(text) == expected


@pytest.mark.parametrize("words, expected", [
    (["augie", "ramen"], '"augie" OR "ramen"'),
    # FTS operators are quoted so they are searched as words
    (["cats", "near", "dogs"], '"cats" OR "near" OR "dogs"'),
    ([], None),
])
def test_full_text_query(words, expected):
    assert memory_storage._full_text_query(words) == expected


# Common word filter

def store_with_common_word(count_with_word: int, total: int, word: str = "augie"):
    store_all(*(
        f"{word} fact{index}" if index < count_with_word else f"other fact{index}"
        for index in range(total)
    ))


def test_drops_words_in_most_memories(fake_model):
    store_with_common_word(count_with_word=8, total=10)
    memory_storage.store_memory("The dog is named Biscuit")
    assert memory_storage._drop_common_words(memory_storage._connection(), ["augie", "biscuit"]) == ["biscuit"]


def test_keeps_words_in_half_the_memories_or_fewer(fake_model):
    store_with_common_word(count_with_word=5, total=10)
    assert memory_storage._drop_common_words(memory_storage._connection(), ["augie"]) == ["augie"]


def test_keeps_all_words_until_there_are_enough_memories(fake_model):
    count_below_minimum = memory_storage.MIN_MEMORIES_FOR_COMMON_WORDS - 1
    store_with_common_word(count_with_word=count_below_minimum, total=count_below_minimum)
    assert memory_storage._drop_common_words(memory_storage._connection(), ["augie"]) == ["augie"]


def test_common_word_count_includes_other_forms_of_the_word(fake_model):
    store_all(*(f"walking fact{index}" for index in range(6)), *(f"other fact{index}" for index in range(4)))
    assert memory_storage._drop_common_words(memory_storage._connection(), ["walks"]) == []


def test_common_name_is_left_out_of_the_word_search(fake_model):
    store_all(*(f"Augie owns gadget{index}" for index in range(10)), "The dog is named Biscuit")
    words = memory_storage._drop_common_words(memory_storage._connection(), memory_storage._search_words("Augie Biscuit"))
    assert memory_storage._full_text_query(words) == '"biscuit"'


# store_memory

def test_creates_database_file_on_first_use(fake_model):
    assert not fake_model.exists()
    memory_storage.store_memory("Augie loves ramen")
    assert fake_model.exists()


def test_returns_new_id_for_each_memory(fake_model):
    first, second = store_all("Augie loves ramen", "The dog is named Biscuit")
    assert first != second


def test_writes_memory_to_all_three_tables(fake_model):
    memory_storage.store_memory("Augie loves ramen")
    assert count("memories") == 1
    assert count("memories_fts") == 1
    assert count("memory_vectors") == 1


def test_strips_surrounding_whitespace(fake_model):
    memory_id = memory_storage.store_memory("  Augie loves ramen \n")
    content = memory_storage._connection().execute(
        "SELECT content FROM memories WHERE id = ?", (memory_id,)
    ).fetchone()[0]
    assert content == "Augie loves ramen"


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_rejects_empty_memory(fake_model, content):
    with pytest.raises(ValueError):
        memory_storage.store_memory(content)


def test_duplicate_returns_existing_id_without_storing(fake_model):
    first, second = store_all("Augie loves ramen", "Augie loves ramen")
    assert first == second
    assert count("memories") == 1
    assert count("memory_vectors") == 1


def test_different_memories_are_not_treated_as_duplicates(fake_model):
    store_all("Augie loves ramen", "Kepler runs on a Raspberry Pi")
    assert count("memories") == 2


def test_memories_survive_reconnecting(fake_model):
    memory_storage.store_memory("Augie loves ramen")
    memory_storage._db.close()
    memory_storage._db = None
    assert memory_storage.recall("ramen") == ["Augie loves ramen"]


def test_failed_vector_insert_leaves_nothing_behind(fake_model):
    first_id = memory_storage.store_memory("Augie loves ramen")
    # Take the id the next memory will get in the vector table, so its vector insert fails after the memories insert
    db = memory_storage._connection()
    with db:
        db.execute(
            "INSERT INTO memory_vectors (memory_id, embedding) VALUES (?, ?)",
            (first_id + 1, fake_embed("something unrelated entirely")),
        )

    with pytest.raises(sqlite3.Error):
        memory_storage.store_memory("The dog is named Biscuit")

    assert count("memories") == 1
    assert count("memories_fts") == 1
    assert memory_storage.recall("Biscuit") == []


def test_concurrent_stores_are_all_saved(fake_model):
    errors = []

    def store(index):
        try:
            memory_storage.store_memory(f"Memory number {index} about topic{index}")
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=store, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert count("memories") == 20
    assert count("memory_vectors") == 20


# recall

@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_returns_nothing(fake_model, query):
    memory_storage.store_memory("Augie loves ramen")
    assert memory_storage.recall(query) == []


def test_empty_database_returns_nothing(fake_model):
    assert memory_storage.recall("ramen") == []


def test_best_match_comes_first(fake_model):
    store_all("Kepler runs on a Raspberry Pi", "Augie loves tonkotsu ramen", "The dog is named Biscuit")
    assert memory_storage.recall("tonkotsu ramen")[0] == "Augie loves tonkotsu ramen"


def test_finds_memory_by_exact_word(fake_model):
    store_all("Kepler runs on a Raspberry Pi", "The dog is named Biscuit")
    assert memory_storage.recall("Biscuit", limit=1) == ["The dog is named Biscuit"]


def test_full_text_search_matches_word_stems(fake_model):
    running_id, _ = store_all("Augie enjoys running in the mornings", "The dog is named Biscuit")
    # The fake embedding treats run and running as unrelated words, so this match comes from the porter stemmer
    assert search_words("run") == [running_id]


@pytest.mark.parametrize("limit", [1, 3])
def test_respects_limit(fake_model, limit):
    store_all(*(f"Fact {index} about subject{index}" for index in range(10)))
    assert len(memory_storage.recall("fact", limit=limit)) == limit


def test_unrelated_memories_are_not_returned(fake_model):
    store_all("Augie loves ramen", "The dog is named Biscuit")
    assert memory_storage.recall("ramen", limit=10) == ["Augie loves ramen"]


@pytest.mark.parametrize("max_distance, expected", [
    (memory_storage.MAX_DISTANCE, ["Augie loves tonkotsu ramen"]),
    (0.1, []),
])
def test_search_by_meaning_skips_candidates_past_max_distance(fake_model, monkeypatch, max_distance, expected):
    memory_storage.store_memory("Augie loves tonkotsu ramen")
    # Leave only the search by meaning, the query shares two of the memory's four words so sits about 0.29 away
    monkeypatch.setattr(memory_storage, "_full_text_query", lambda words: None)
    monkeypatch.setattr(memory_storage, "MAX_DISTANCE", max_distance)
    assert memory_storage.recall("tonkotsu ramen") == expected


# Reranking

def test_returns_memories_in_reranker_order(scores):
    store_all("ramen one", "ramen two", "ramen three")
    scores.update({"ramen one": 1.0, "ramen two": 3.0, "ramen three": 2.0})
    assert memory_storage.recall("ramen") == ["ramen two", "ramen three", "ramen one"]


def test_drops_memories_below_min_rerank_score(scores):
    store_all("ramen one", "ramen two")
    scores.update({"ramen one": memory_storage.MIN_RERANK_SCORE - 1, "ramen two": memory_storage.MIN_RERANK_SCORE - 0.5})
    assert memory_storage.recall("ramen") == []


def test_drops_memories_too_far_behind_the_best(scores):
    store_all("ramen one", "ramen two", "ramen three")
    gap = memory_storage.RERANK_SCORE_GAP
    scores.update({"ramen one": 5.0, "ramen two": 5.0 - gap + 0.1, "ramen three": 5.0 - gap - 0.1})
    assert memory_storage.recall("ramen") == ["ramen one", "ramen two"]


def test_limit_applies_after_reranking(scores):
    store_all("ramen one", "ramen two", "ramen three")
    scores.update({"ramen one": 1.0, "ramen two": 3.0, "ramen three": 2.0})
    assert memory_storage.recall("ramen", limit=1) == ["ramen two"]


def test_reranks_at_most_two_searches_worth_of_candidates(scores):
    contents = [f"ramen fact{index} detail{index}" for index in range(30)]
    store_all(*contents)
    scores.update({content: 1.0 for content in contents})
    memory_storage.recall("ramen")
    assert 0 < len(scores["reranked"][0]) <= 2 * memory_storage.CANDIDATES_PER_SEARCH


def test_each_candidate_is_reranked_once(scores):
    # Found by both searches, still only scored once
    store_all("Augie loves ramen")
    scores.update({"Augie loves ramen": 1.0})
    memory_storage.recall("Augie loves ramen")
    assert scores["reranked"] == [["Augie loves ramen"]]


def test_reranker_not_called_without_candidates(scores):
    store_all("Augie loves ramen")
    memory_storage.recall("Biscuit")
    assert scores["reranked"] == []


def test_stopwords_alone_do_not_make_a_word_match(fake_model):
    memory_storage.store_memory("Kepler is orange")
    assert search_words("what is it") == []


def test_returns_each_memory_once(fake_model):
    store_all("Augie loves ramen", "Augie loves udon", "The dog is named Biscuit")
    results = memory_storage.recall("Augie loves ramen")
    assert len(results) == len(set(results))


@pytest.mark.parametrize("query", ['what\'s "up"', "ramen AND", "NOT", "-ramen", "ramen*", "(ramen", "?!", "column:ramen"])
def test_query_with_fts_syntax_does_not_raise(fake_model, query):
    memory_storage.store_memory("Augie loves ramen")
    assert isinstance(memory_storage.recall(query), list)


def test_marks_only_returned_memories_as_used(fake_model):
    ramen_id, dog_id = store_all("Augie loves ramen", "The dog is named Biscuit")
    memory_storage.recall("ramen", limit=1)
    last_used = dict(memory_storage._connection().execute("SELECT id, last_used FROM memories"))
    assert last_used[ramen_id] is not None
    assert last_used[dog_id] is None


# The memories_fts index is kept up to date by triggers, so editing memories directly must update it too

def test_updating_content_reindexes_it(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    db = memory_storage._connection()
    with db:
        db.execute("UPDATE memories SET content = ? WHERE id = ?", ("Augie loves udon", memory_id))
    assert search_words("ramen") == []
    assert search_words("udon") == [memory_id]


def test_deleting_memory_removes_it_from_index(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    db = memory_storage._connection()
    with db:
        db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    assert search_words("ramen") == []


# Real models, downloaded on first run

SAMPLE_MEMORIES = [
    "Augie loves tonkotsu ramen", "Kepler runs on a Raspberry Pi 5", "The dog is named Biscuit",
    "Augie works as a software engineer", "Augie hates waking up early", "Augie's sister lives in Denver",
    "Kepler's favorite color is orange", "Augie is allergic to peanuts",
    # Enough memories, most about Augie, that the common word filter leaves "augie" out of the word search
    "Augie drives a blue Subaru", "Augie plays guitar on weekends", "Augie collects vinyl records",
]

def test_rewording_is_treated_as_duplicate(real_model):
    first, second = store_all("Augie loves tonkotsu ramen", "Augie really loves tonkotsu ramen")
    assert first == second


def test_related_but_different_facts_are_both_kept(real_model):
    store_all("Augie loves ramen", "Augie hates mornings")
    assert count("memories") == 2


def test_finds_memory_by_meaning_without_shared_words(real_model):
    store_all("Kepler runs on a Raspberry Pi 5", "The dog is named Biscuit", "Augie works as a software engineer")
    assert memory_storage.recall("what is the pet called", limit=1) == ["The dog is named Biscuit"]


@pytest.mark.parametrize("query", ["what's the weather today", "tell me a joke", "how tall is mount everest"])
def test_unrelated_query_recalls_nothing(real_model, query):
    store_all("Augie loves tonkotsu ramen", "The dog is named Biscuit", "Kepler's favorite color is orange")
    assert memory_storage.recall(query) == []


@pytest.mark.parametrize("query, expected", [
    ("what's Augie's job", ["Augie works as a software engineer"]),
    ("is Augie a morning person", ["Augie hates waking up early"]),
    ("where does Augie's family live", ["Augie's sister lives in Denver"]),
])
def test_memories_sharing_only_a_name_are_not_recalled(real_model, query, expected):
    store_all(*SAMPLE_MEMORIES)
    assert memory_storage.recall(query) == expected


def test_finds_weak_but_correct_match(real_model):
    store_all(*SAMPLE_MEMORIES)
    assert memory_storage.recall("what hardware am I running on")[0] == "Kepler runs on a Raspberry Pi 5"


def test_embeddings_are_normalized_with_expected_dimensions(real_model):
    vector = np.frombuffer(memory_storage._embed("Augie loves ramen"), dtype=np.float32)
    assert vector.shape == (memory_storage.EMBEDDING_DIMENSIONS,)
    assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-5)


# Updating and forgetting

def test_update_changes_content_and_reindexes_words(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    assert memory_storage.update_memory(memory_id, "Augie loves udon")
    assert memory_storage.recall("udon") == ["Augie loves udon"]
    assert memory_storage.recall("ramen") == []


def test_update_replaces_the_embedding(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    memory_storage.update_memory(memory_id, "The dog is named Biscuit")
    nearest = memory_storage._connection().execute(
        "SELECT memory_id, distance FROM memory_vectors WHERE embedding MATCH ? AND k = 1",
        (fake_embed("The dog is named Biscuit"),),
    ).fetchone()
    assert nearest[0] == memory_id
    assert nearest[1] == pytest.approx(0.0, abs=1e-5)


def test_update_of_missing_memory_returns_false(fake_model):
    assert memory_storage.update_memory(999, "Augie loves udon") is False
    assert count("memories") == 0


def test_update_rejects_empty_content(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    with pytest.raises(ValueError):
        memory_storage.update_memory(memory_id, "  ")


def test_forget_removes_memory_from_all_three_tables(fake_model):
    memory_id, _ = store_all("Augie loves ramen", "The dog is named Biscuit")
    assert memory_storage.forget_memory(memory_id)
    assert count("memories") == 1
    assert count("memories_fts") == 1
    assert count("memory_vectors") == 1
    assert memory_storage.recall("ramen") == []


def test_forget_of_missing_memory_returns_false(fake_model):
    assert memory_storage.forget_memory(999) is False


def test_recall_with_ids_pairs_ids_with_content(fake_model):
    ramen_id, dog_id = store_all("Augie loves ramen", "The dog is named Biscuit")
    assert memory_storage.recall_with_ids("Biscuit") == [(dog_id, "The dog is named Biscuit")]


def test_recall_with_ids_can_leave_memories_unmarked(fake_model):
    memory_id = memory_storage.store_memory("Augie loves ramen")
    memory_storage.recall_with_ids("ramen", mark_used=False)
    last_used = memory_storage._connection().execute("SELECT last_used FROM memories WHERE id = ?", (memory_id,)).fetchone()[0]
    assert last_used is None
