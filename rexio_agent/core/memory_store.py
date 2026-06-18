"""
File-backed persistent memory for RexiO Agent.

Two stores:
  - MEMORY.md  : agent's personal notes (env facts, project conventions, tool quirks)
  - USER.md    : what the agent knows about the user (name, prefs, habits, style)

Frozen snapshot pattern (same as Hermes):
  - Loaded once at session start → injected into system prompt
  - Mid-session writes persist to disk immediately but do NOT change the system
    prompt — keeps context stable for the entire session
  - Snapshot refreshes on next session start

Entry delimiter: § (section sign). Entries can be multiline.
Character limits: 2200 chars (memory) / 1375 chars (user).
"""

import os
import re
import json
import tempfile
from typing import Dict, List, Optional

ENTRY_DELIMITER = "\n§\n"
MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "memories"
)

_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'do\s+not\s+tell\s+the\s+user', "deception"),
    (r'system\s+prompt\s+override', "sys_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules)', "disregard_rules"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)', "exfil_curl"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc)', "read_secrets"),
]
_INVISIBLE = {'​', '‌', '‍', '⁠', '﻿'}


def _scan(content: str) -> Optional[str]:
    for ch in _INVISIBLE:
        if ch in content:
            return f"Blocked: invisible unicode U+{ord(ch):04X} detected."
    for pattern, pid in _THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: threat pattern '{pid}'."
    return None


def _read_file(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        raw = open(path, encoding="utf-8").read()
    except OSError:
        return []
    if not raw.strip():
        return []
    entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
    return [e for e in entries if e]


def _write_file(path: str, entries: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = ENTRY_DELIMITER.join(entries) if entries else ""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class MemoryStore:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._mem_path = os.path.join(DATA_DIR, "MEMORY.md")
        self._user_path = os.path.join(DATA_DIR, "USER.md")
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        # Frozen snapshot — set once at load(), never mutated mid-session
        self._snapshot: Dict[str, str] = {"memory": "", "user": ""}

    def load(self):
        """Load from disk and capture frozen snapshot for system prompt."""
        self.memory_entries = list(dict.fromkeys(_read_file(self._mem_path)))
        self.user_entries = list(dict.fromkeys(_read_file(self._user_path)))
        self._snapshot = {
            "memory": self._render("memory", self.memory_entries),
            "user": self._render("user", self.user_entries),
        }

    # ── Public tool actions ──────────────────────────────────────────────────

    def add(self, target: str, content: str) -> Dict:
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}
        err = _scan(content)
        if err:
            return {"success": False, "error": err}

        entries = self._entries(target)
        limit = USER_CHAR_LIMIT if target == "user" else MEMORY_CHAR_LIMIT

        if content in entries:
            return self._ok(target, "Already exists — no duplicate added.")

        new_entries = entries + [content]
        if len(ENTRY_DELIMITER.join(new_entries)) > limit:
            used = len(ENTRY_DELIMITER.join(entries))
            return {"success": False, "error": f"Memory full ({used}/{limit} chars). Replace or remove entries first."}

        entries.append(content)
        self._set(target, entries)
        _write_file(self._path(target), entries)
        return self._ok(target, "Entry added.")

    def replace(self, target: str, old_text: str, content: str) -> Dict:
        old_text, content = old_text.strip(), content.strip()
        if not old_text or not content:
            return {"success": False, "error": "old_text and content are required."}
        err = _scan(content)
        if err:
            return {"success": False, "error": err}

        entries = self._entries(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1 and len({e for _, e in matches}) > 1:
            return {"success": False, "error": f"Multiple entries matched '{old_text}'. Be more specific."}

        entries[matches[0][0]] = content
        self._set(target, entries)
        _write_file(self._path(target), entries)
        return self._ok(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict:
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text is required."}

        entries = self._entries(target)
        matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
        if not matches:
            return {"success": False, "error": f"No entry matched '{old_text}'."}
        if len(matches) > 1 and len({e for _, e in matches}) > 1:
            return {"success": False, "error": f"Multiple entries matched '{old_text}'. Be more specific."}

        entries.pop(matches[0][0])
        self._set(target, entries)
        _write_file(self._path(target), entries)
        return self._ok(target, "Entry removed.")

    # ── System prompt injection ──────────────────────────────────────────────

    def system_prompt_block(self) -> str:
        """Returns frozen snapshot block for system prompt injection."""
        parts = []
        if self._snapshot["user"]:
            parts.append(self._snapshot["user"])
        if self._snapshot["memory"]:
            parts.append(self._snapshot["memory"])
        return "\n\n".join(parts)

    # ── Internals ────────────────────────────────────────────────────────────

    def _path(self, target: str) -> str:
        return self._user_path if target == "user" else self._mem_path

    def _entries(self, target: str) -> List[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _render(self, target: str, entries: List[str]) -> str:
        if not entries:
            return ""
        limit = USER_CHAR_LIMIT if target == "user" else MEMORY_CHAR_LIMIT
        content = ENTRY_DELIMITER.join(entries)
        used = len(content)
        pct = min(100, int(used / limit * 100))
        header = (
            f"USER PROFILE [{pct}% — {used}/{limit} chars]"
            if target == "user" else
            f"MEMORY [{pct}% — {used}/{limit} chars]"
        )
        sep = "─" * 44
        return f"{sep}\n{header}\n{sep}\n{content}"

    def _ok(self, target: str, msg: str) -> Dict:
        entries = self._entries(target)
        limit = USER_CHAR_LIMIT if target == "user" else MEMORY_CHAR_LIMIT
        used = len(ENTRY_DELIMITER.join(entries)) if entries else 0
        return {
            "success": True,
            "message": msg,
            "entries": entries,
            "usage": f"{used}/{limit} chars",
        }


MEMORY_TOOL_SCHEMA = """\
- memory(action, target, content=None, old_text=None):
  Description: Save durable information to persistent memory that survives across sessions.
  Memory is injected into every future session automatically.

  WHEN TO SAVE (do this proactively, without being asked):
  - User corrects you or says "remember this" / "don't do that again"
  - User shares a preference, name, role, timezone, coding style, or habit
  - You discover something about the environment (OS, tools installed, project structure)
  - You learn a convention, API quirk, or workflow specific to this setup
  - You identify a stable fact useful in future sessions

  TWO TARGETS:
  - 'user'   : who the user is — name, role, preferences, communication style
  - 'memory' : your notes — env facts, project conventions, tool quirks, lessons

  ACTIONS:
  - add(target, content)              : append a new entry
  - replace(target, old_text, content): update entry containing old_text substring
  - remove(target, old_text)          : delete entry containing old_text substring

  SKIP: trivial info, things easily re-discovered, temporary task state.
"""
