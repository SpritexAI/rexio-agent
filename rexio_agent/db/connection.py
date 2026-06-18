import os
import sqlite3
from typing import List, Dict, Any, Optional

from rexio_agent.core.config import DB_DIR, DB_PATH
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
MD_SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")

def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _seed_default_skills() -> None:
    """Seeds default markdown skills if none exist yet."""
    try:
        existing = get_markdown_skills()
        if existing:
            return
        from rexio_agent.db.seed_skills import SKILLS
        for skill in SKILLS:
            save_markdown_skill(skill["name"], skill["description"], skill["content"])
    except Exception:
        pass

def init_db() -> None:
    """Initializes the database using the schema.sql file."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        conn.executescript(schema_sql)
        _seed_default_skills()

        # Migrations for existing DBs
        migrations = [
            "ALTER TABLE messages ADD COLUMN steps_json TEXT",
            "ALTER TABLE skills ADD COLUMN status TEXT DEFAULT 'pending'",
        ]
        for migration in migrations:
            try:
                conn.execute(migration)
                conn.commit()
            except Exception:
                pass  # Column already exists

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

def save_message(conv_id: str, role: str, content: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conv_id, role, content)
        )
        conn.commit()
        return cursor.lastrowid

def update_message_steps(msg_id: int, steps_json: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE messages SET steps_json = ? WHERE id = ?",
            (steps_json, msg_id)
        )
        conn.commit()

def get_messages(conv_id: str) -> List[Dict[str, Any]]:
    import json as _json
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, steps_json, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,)
        ).fetchall()
        result = []
        for row in rows:
            r = dict(row)
            r["steps"] = _json.loads(r.pop("steps_json")) if r.get("steps_json") else []
            result.append(r)
        return result

# --- Skills Helpers ---

def save_skill(name: str, description: str, code: str, status: str = 'pending') -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO skills (name, description, code, status, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                code = excluded.code,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, description, code, status)
        )
        conn.commit()

def get_skills() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT name, description, code, status, created_at, updated_at FROM skills"
        ).fetchall()
        return [dict(row) for row in rows]

def get_active_skills() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT name, description, code FROM skills WHERE status = 'active'"
        ).fetchall()
        return [dict(row) for row in rows]

def get_pending_skills() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT name, description, code, created_at FROM skills WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

def approve_skill(name: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE skills SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE name = ?",
            (name,)
        )
        conn.commit()

def reject_skill(name: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM skills WHERE name = ?", (name,))
        conn.commit()

def get_skill(name: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT name, description, code, status, created_at, updated_at FROM skills WHERE name = ?",
            (name,)
        ).fetchone()
        return dict(row) if row else None

# --- Markdown Skills Helpers ---

def save_markdown_skill(name: str, description: str, content: str) -> None:
    # Save to DB
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO markdown_skills (name, description, content, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                content = excluded.content,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, description, content)
        )
        conn.commit()
    # Save to .md file
    os.makedirs(MD_SKILLS_DIR, exist_ok=True)
    md_path = os.path.join(MD_SKILLS_DIR, f"{name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"---\nname: {name}\ndescription: {description}\n---\n\n{content}")

def get_markdown_skills() -> List[Dict[str, Any]]:
    """Load markdown skills — file system is source of truth, DB is index."""
    os.makedirs(MD_SKILLS_DIR, exist_ok=True)
    skills = []
    # Read from .md files directly
    for fname in sorted(os.listdir(MD_SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(MD_SKILLS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            raw = f.read()
        # Parse frontmatter
        name = fname[:-3]
        description = ""
        content = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                content = parts[2].strip()
                for line in fm.splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
        skills.append({"name": name, "description": description, "content": content})
    return skills

def delete_markdown_skill(name: str) -> None:
    # Remove from DB
    with get_db_connection() as conn:
        conn.execute("DELETE FROM markdown_skills WHERE name = ?", (name,))
        conn.commit()
    # Remove .md file
    md_path = os.path.join(MD_SKILLS_DIR, f"{name}.md")
    if os.path.exists(md_path):
        os.remove(md_path)

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
