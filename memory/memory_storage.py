import logging
import re
import sqlite3
import threading
from pathlib import Path

import numpy as np
import sqlite_vec
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder

DB_PATH = Path(__file__).with_name("kepler_memory.db")

# Small enough to run on the Pi, 384 dimensions. Changing it means re-embedding every stored memory.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

# Cosine distance under which a new memory counts as a rewording of one already stored
DUPLICATE_DISTANCE = 0.1
# Scores how well each candidate answers the query, reading both together. 80MB, about 30ms for 20 candidates on a Mac.
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"

# The two searches only gather candidates and the reranker decides relevance, so these are kept loose
# Cosine distance past which a search-by-meaning result isn't worth reranking. Measured on sample data:
# correct matches landed at 0.18-0.79, unrelated queries at 0.87-0.89.
MAX_DISTANCE = 0.9
# How many candidates each search contributes, so at most twice this many get reranked
CANDIDATES_PER_SEARCH = 10

# Reranker score below which a memory is not relevant at all. Measured on sample data: correct matches
# scored -4.9 to 7.9, memories for unrelated queries -10.9 or lower.
MIN_RERANK_SCORE = -8.0
# How far behind the best memory another can score and still be returned. Scores are only comparable within
# one query, so this drops memories that only share a name with the question. Measured on sample data:
# memories that weren't the answer scored at least 3.5 behind it.
RERANK_SCORE_GAP = 3.0
# Words in more than this share of memories (like "Augie" or "Kepler") match too much to help a word search
COMMON_WORD_FRACTION = 0.5
# Below this many memories every word looks common, so the filter waits until there are enough to judge
MIN_MEMORIES_FOR_COMMON_WORDS = 10

# Words too common to be worth matching on in a word search, the search by meaning still sees them
STOPWORDS = frozenset("""
    a about am an and any are as at be been but by can could did do does doing for from had has have
    he her hers him his how i if in into is it its just me my no not of on or our ours she should so
    some than that the their theirs them then there these they this those to too up us very was we
    were what when where which who whom why will with would you your yours
    s t m d ll re ve
""".split())

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_used   TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, content='memories', content_rowid='id', tokenize='porter'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF content ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content);
    INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
    memory_id INTEGER PRIMARY KEY,
    embedding FLOAT[{EMBEDDING_DIMENSIONS}] distance_metric=cosine
);
"""

# One connection shared across threads, the lock keeps them from using it at the same time
_lock = threading.Lock()
_db = None
_model = None
_reranker = None


def _connection() -> sqlite3.Connection:
    """
    Open the database on first use, creating the file and tables if they are missing.
    """
    global _db
    if _db is None:
        logging.info("Opening memory database at %s", DB_PATH)
        db = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(SCHEMA)
        _db = db
    return _db


def warm_up():
    """
    Open the database and load both models now, so the first memory stored or recalled isn't slow.
    """
    with _lock:
        _connection()
    _embed("warm up")
    _rerank("warm up", ["warm up"])
    logging.info("Memory storage ready")


def _embed(text: str) -> bytes:
    """
    Turn text into a normalized vector packed the way sqlite-vec stores it.
    """
    global _model
    if _model is None:
        logging.info("Loading embedding model %s", EMBEDDING_MODEL)
        _model = TextEmbedding(EMBEDDING_MODEL)
    vector = next(iter(_model.embed([text])))
    vector = vector / np.linalg.norm(vector)
    return sqlite_vec.serialize_float32(vector.tolist())


def _rerank(query: str, texts: list[str]) -> list[float]:
    """
    Score each text for how well it answers the query, higher is better, in the same order as the texts.
    """
    global _reranker
    if _reranker is None:
        logging.info("Loading reranker model %s", RERANK_MODEL)
        _reranker = TextCrossEncoder(RERANK_MODEL)
    return [float(score) for score in _reranker.rerank(query, texts)]


def _search_words(text: str) -> list[str]:
    """
    The words of the query worth matching on, lowercased, without stopwords or repeats.
    """
    words = [word for word in re.findall(r"\w+", text.lower()) if word not in STOPWORDS]
    return list(dict.fromkeys(words))


def _drop_common_words(db: sqlite3.Connection, words: list[str]) -> list[str]:
    """
    Remove words that appear in so many memories that matching them says little, like names.
    Counts through the full-text index so word stems are counted the same way the search matches them.
    """
    total = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    if total < MIN_MEMORIES_FOR_COMMON_WORDS:
        return words

    distinctive = []
    for word in words:
        matches = db.execute("SELECT COUNT(*) FROM memories_fts WHERE memories_fts MATCH ?", (f'"{word}"',)).fetchone()[0]
        if matches / total <= COMMON_WORD_FRACTION:
            distinctive.append(word)
    return distinctive


def _full_text_query(words: list[str]) -> str | None:
    """
    Quote every word so punctuation and words like AND or NOT in the query can't break FTS5 syntax.
    """
    return " OR ".join(f'"{word}"' for word in words) or None


def store_memory(content: str) -> int:
    """
    Save a memory and return its id. If a memory saying the same thing is already stored, returns that one's id instead.
    """
    content = content.strip()
    if not content:
        raise ValueError("Cannot store an empty memory")

    # Embed outside the lock, inference takes far longer than the database writes
    vector = _embed(content)

    with _lock:
        db = _connection()
        nearest = db.execute(
            "SELECT memory_id, distance FROM memory_vectors WHERE embedding MATCH ? AND k = 1",
            (vector,),
        ).fetchone()
        if nearest and nearest[1] < DUPLICATE_DISTANCE:
            logging.info("Memory %r duplicates memory %d (distance %.3f), not storing it", content, nearest[0], nearest[1])
            return nearest[0]

        # One transaction so a memory is never searchable by its words but not its meaning, or the other way round
        with db:
            memory_id = db.execute("INSERT INTO memories (content) VALUES (?)", (content,)).lastrowid
            db.execute("INSERT INTO memory_vectors (memory_id, embedding) VALUES (?, ?)", (memory_id, vector))

    logging.info("Stored memory %d: %r", memory_id, content)
    return memory_id


def update_memory(memory_id: int, content: str) -> bool:
    """
    Replace what a memory says, for when a fact has changed. Returns False if there is no memory with that id.
    """
    content = content.strip()
    if not content:
        raise ValueError("Cannot update a memory to be empty")

    vector = _embed(content)

    with _lock:
        db = _connection()
        with db:
            # The memories_au trigger reindexes the words
            updated = db.execute("UPDATE memories SET content = ? WHERE id = ?", (content, memory_id)).rowcount
            if updated:
                db.execute("UPDATE memory_vectors SET embedding = ? WHERE memory_id = ?", (vector, memory_id))

    if updated:
        logging.info("Updated memory %d: %r", memory_id, content)
    else:
        logging.warning("Could not update memory %d, it does not exist", memory_id)
    return bool(updated)


def forget_memory(memory_id: int) -> bool:
    """
    Delete a memory. Returns False if there is no memory with that id.
    """
    with _lock:
        db = _connection()
        with db:
            # vec0 tables don't take part in foreign keys, so the vector has to be deleted by hand
            db.execute("DELETE FROM memory_vectors WHERE memory_id = ?", (memory_id,))
            # The memories_ad trigger removes the words from the index
            deleted = db.execute("DELETE FROM memories WHERE id = ?", (memory_id,)).rowcount

    if deleted:
        logging.info("Forgot memory %d", memory_id)
    else:
        logging.warning("Could not forget memory %d, it does not exist", memory_id)
    return bool(deleted)


def recall(query: str, limit: int = 5) -> list[str]:
    """
    Find the stored memories most relevant to the query, best match first.
    """
    return [content for _, content in recall_with_ids(query, limit)]


def recall_with_ids(query: str, limit: int = 5, mark_used: bool = True) -> list[tuple[int, str]]:
    """
    Find the stored memories most relevant to the query as (id, content) pairs, best match first.
    A search by meaning and a search by exact words gather candidates, so both "what does Augie like to eat"
    and an exact name find the right memory, then a reranker reads each candidate against the query to
    decide which are relevant.
    mark_used is False for lookups that aren't the memory being used, like checking for related memories.
    """
    query = query.strip()
    if not query:
        return []

    vector = _embed(query)
    words = _search_words(query)

    with _lock:
        db = _connection()
        by_meaning = [memory_id for memory_id, distance in db.execute(
            "SELECT memory_id, distance FROM memory_vectors WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (vector, CANDIDATES_PER_SEARCH),
        ) if distance <= MAX_DISTANCE]

        by_words = []
        full_text_query = _full_text_query(_drop_common_words(db, words))
        if full_text_query:
            by_words = [row[0] for row in db.execute(
                "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
                (full_text_query, CANDIDATES_PER_SEARCH),
            )]

        candidate_ids = list(dict.fromkeys(by_meaning + by_words))
        if not candidate_ids:
            return []
        placeholders = ",".join("?" * len(candidate_ids))
        candidates = list(db.execute(f"SELECT id, content FROM memories WHERE id IN ({placeholders})", candidate_ids))

    if not candidates:
        return []

    # Rerank outside the lock, inference takes far longer than the database reads
    scores = _rerank(query, [content for _, content in candidates])
    ranked = sorted(zip(scores, candidates), key=lambda pair: pair[0], reverse=True)
    cutoff = max(MIN_RERANK_SCORE, ranked[0][0] - RERANK_SCORE_GAP)
    best = [(memory_id, content) for score, (memory_id, content) in ranked if score >= cutoff][:limit]
    logging.debug("Reranked %d candidates for %r, top score %.2f, kept %d", len(candidates), query, ranked[0][0], len(best))
    if not best:
        return []

    if mark_used:
        with _lock:
            db = _connection()
            best_ids = [memory_id for memory_id, _ in best]
            with db:
                db.execute(f"UPDATE memories SET last_used = datetime('now') WHERE id IN ({','.join('?' * len(best_ids))})", best_ids)

    logging.info("Recalled %d memories for %r", len(best), query)
    return best
