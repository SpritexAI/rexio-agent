import os
import sqlite3
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "aethelis.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """Initializes the database using the schema.sql file."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")
    
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    
    with get_db_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()

# --- Conversation & Message Helpers ---

def save_conversation(conv_id: str, platform: str, channel_id: str, summary: Optional[str] = None) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, platform, channel_id, summary)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                summary = excluded.summary
            """,
            (conv_id, platform, channel_id, summary)
        )
        conn.commit()

def save_message(conv_id: str, role: str, content: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conv_id, role, content)
        )
        conn.commit()

def get_messages(conv_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,)
        ).fetchall()
        return [dict(row) for row in rows]

# --- Skills Helpers ---

def save_skill(name: str, description: str, code: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO skills (name, description, code, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                code = excluded.code,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, description, code)
        )
        conn.commit()

def get_skills() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, description, code, created_at, updated_at FROM skills").fetchall()
        return [dict(row) for row in rows]

def get_skill(name: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT name, description, code, created_at, updated_at FROM skills WHERE name = ?",
            (name,)
        ).fetchone()
        return dict(row) if row else None

# --- Tasks Helpers ---

def save_task(task_id: str, name: str, schedule: str, prompt: str, platform: str, channel_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, name, schedule, prompt, platform, channel_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                schedule = excluded.schedule,
                prompt = excluded.prompt,
                status = excluded.status
            """,
            (task_id, name, schedule, prompt, platform, channel_id)
        )
        conn.commit()

def get_tasks() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, name, schedule, prompt, platform, channel_id, last_run, status FROM tasks").fetchall()
        return [dict(row) for row in rows]

def update_task_last_run(task_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE tasks SET last_run = CURRENT_TIMESTAMP WHERE id = ?",
            (task_id,)
        )
        conn.commit()

# --- Memory Helpers ---

def save_memory(key: str, value: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO memories (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value)
        )
        conn.commit()

def get_memory(key: str) -> Optional[str]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM memories WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

def get_all_memories() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT key, value, updated_at FROM memories").fetchall()
        return [dict(row) for row in rows]
