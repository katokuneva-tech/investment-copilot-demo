"""Persistent response cache using SQLite."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "cache.db"
TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS response_cache (
            cache_key TEXT PRIMARY KEY,
            skill_id TEXT,
            message TEXT,
            response_json TEXT,
            created_at REAL
        )
    """)
    conn.commit()
    return conn


_conn = _get_conn()


def cache_key(skill_id: str, message: str, doc_ids: list[str], provider: str = "") -> str:
    raw = f"{provider}:{skill_id}:{message.lower().strip()}:{':'.join(sorted(doc_ids))}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(key: str) -> dict | None:
    """Get cached response. Returns None if not found or expired."""
    try:
        row = _conn.execute(
            "SELECT response_json, created_at FROM response_cache WHERE cache_key = ?",
            (key,)
        ).fetchone()
        if row is None:
            return None
        response_json, created_at = row
        if time.time() - created_at > TTL_SECONDS:
            _conn.execute("DELETE FROM response_cache WHERE cache_key = ?", (key,))
            _conn.commit()
            return None
        return json.loads(response_json)
    except Exception as e:
        print(f"[CACHE] Read error: {e}")
        return None


def set_cached(key: str, skill_id: str, message: str, response: dict):
    """Store response in cache."""
    try:
        _conn.execute(
            "INSERT OR REPLACE INTO response_cache (cache_key, skill_id, message, response_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (key, skill_id, message, json.dumps(response, ensure_ascii=False), time.time())
        )
        _conn.commit()
    except Exception as e:
        print(f"[CACHE] Write error: {e}")


def clear_cache():
    """Clear all cached responses."""
    try:
        _conn.execute("DELETE FROM response_cache")
        _conn.commit()
        print("[CACHE] Cleared")
    except Exception as e:
        print(f"[CACHE] Clear error: {e}")


def cleanup_expired():
    """Remove expired entries."""
    try:
        cutoff = time.time() - TTL_SECONDS
        deleted = _conn.execute(
            "DELETE FROM response_cache WHERE created_at < ?", (cutoff,)
        ).rowcount
        _conn.commit()
        if deleted:
            print(f"[CACHE] Cleaned {deleted} expired entries")
    except Exception as e:
        print(f"[CACHE] Cleanup error: {e}")
