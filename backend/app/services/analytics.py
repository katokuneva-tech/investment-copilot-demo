"""Request logging and analytics via SQLite."""
import sqlite3
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        user_name TEXT,
        skill_id TEXT,
        message TEXT,
        response_time_ms INTEGER,
        provider TEXT,
        status TEXT DEFAULT 'ok',
        error TEXT
    )""")
    db.commit()
    return db


def log_request(user_name: str, skill_id: str, message: str,
                response_time_ms: int, provider: str = "", status: str = "ok", error: str = ""):
    try:
        db = _get_db()
        db.execute(
            "INSERT INTO requests (timestamp, user_name, skill_id, message, response_time_ms, provider, status, error) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(), user_name, skill_id, message[:500], response_time_ms, provider, status, error),
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[ANALYTICS] Log error: {e}")


def get_dashboard() -> dict:
    """Get analytics dashboard data."""
    try:
        db = _get_db()

        # Total requests
        total = db.execute("SELECT COUNT(*) as c FROM requests").fetchone()["c"]

        # Last 24h
        since_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        last_24h = db.execute("SELECT COUNT(*) as c FROM requests WHERE timestamp > ?", (since_24h,)).fetchone()["c"]

        # Avg response time
        avg_time = db.execute("SELECT AVG(response_time_ms) as a FROM requests WHERE status='ok'").fetchone()["a"]

        # By skill
        by_skill = [dict(r) for r in db.execute(
            "SELECT skill_id, COUNT(*) as count, AVG(response_time_ms) as avg_ms FROM requests GROUP BY skill_id ORDER BY count DESC"
        ).fetchall()]

        # By user
        by_user = [dict(r) for r in db.execute(
            "SELECT user_name, COUNT(*) as count, MAX(timestamp) as last_seen FROM requests GROUP BY user_name ORDER BY count DESC"
        ).fetchall()]

        # Errors
        errors = db.execute("SELECT COUNT(*) as c FROM requests WHERE status='error'").fetchone()["c"]

        # Recent requests (last 50)
        recent = [dict(r) for r in db.execute(
            "SELECT timestamp, user_name, skill_id, message, response_time_ms, provider, status FROM requests ORDER BY id DESC LIMIT 50"
        ).fetchall()]

        # Hourly distribution (last 24h)
        hourly = [dict(r) for r in db.execute(
            "SELECT strftime('%H', timestamp) as hour, COUNT(*) as count FROM requests WHERE timestamp > ? GROUP BY hour ORDER BY hour",
            (since_24h,),
        ).fetchall()]

        db.close()

        return {
            "total_requests": total,
            "last_24h": last_24h,
            "avg_response_ms": round(avg_time or 0),
            "error_count": errors,
            "by_skill": by_skill,
            "by_user": by_user,
            "recent": recent,
            "hourly": hourly,
        }
    except Exception as e:
        return {"error": str(e)}
