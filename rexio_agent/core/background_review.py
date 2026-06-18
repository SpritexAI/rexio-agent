"""
Background self-improvement review — runs after every agent turn.

Spawns a daemon thread that asks the LLM:
  1. Should anything be saved to memory?
  2. Should a skill be created from this workflow?

Uses only memory + skill tools. Never touches the main conversation.
Fires a callback (e.g. Telegram notification) with the summary.
"""

import re
import ast
import json
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Review prompts (adapted from Hermes) ─────────────────────────────────────

MEMORY_REVIEW_PROMPT = """Review the conversation above and decide if anything should be saved to persistent memory.

Focus on:
1. Has the user revealed personal details — name, role, preferences, communication style, timezone?
2. Has the user corrected your behavior or expressed expectations about how you should work?
3. Did you discover something about the environment — OS, tools installed, project structure, API quirks?

If something stands out, respond with ONLY the memory tool call(s) in this exact format:
  Action: memory(action="add", target="user", content="...")
  Action: memory(action="add", target="memory", content="...")

If nothing is worth saving, respond with exactly: Nothing to save."""

SKILL_REVIEW_PROMPT = """Review the conversation above and decide if a reusable skill should be created.

A skill is worth creating if:
- A multi-step workflow was completed successfully (web research + analysis, file operations, code execution)
- The user corrected your style/format in a way that should be remembered as a rule
- A repeatable task pattern emerged that would save time in future sessions

If a skill should be created, respond with ONLY:
  Action: save_recent_workflow_as_tool(task_description="<short description of what was done>")

If nothing is worth creating, respond with exactly: Nothing to create."""

SYSTEM_PROMPT = """You are a self-improvement assistant reviewing a completed agent conversation.
Your job is to extract learnings and save them. Be selective but proactive.
Respond ONLY with Action: tool_call(...) lines or the exact "Nothing to save/create" phrase.
Do not explain. Do not add commentary."""


def _parse_action(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parse 'Action: tool_name(key="val")' from LLM response."""
    match = re.search(r'Action:\s*([a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?\))', text, re.DOTALL)
    if not match:
        return None
    try:
        expr = match.group(1).strip()
        tree = ast.parse(expr)
        if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
            call = tree.body[0].value
            if isinstance(call, ast.Call):
                name = call.func.id
                kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
                return name, kwargs
    except Exception:
        pass
    return None


def _build_context(user_input: str, assistant_response: str, history: List[Dict]) -> str:
    """Build conversation context string for the review prompt."""
    parts = []
    # Include last 3 exchanges for context
    recent = history[-6:] if len(history) > 6 else history
    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        parts.append(f"{role}: {msg.get('content', '')[:500]}")
    parts.append(f"User: {user_input}")
    parts.append(f"Assistant: {assistant_response[:1000]}")
    return "\n".join(parts)


def run_background_review(
    llm,
    memory_store,
    registry,
    user_input: str,
    assistant_response: str,
    history: List[Dict],
    execution_log: List[Dict],
    callback: Optional[Callable[[str], None]] = None,
) -> None:
    """Runs in background thread — reviews turn, saves memory/skills as needed."""
    actions_taken = []
    context = _build_context(user_input, assistant_response, history)

    # ── 1. Memory review ──────────────────────────────────────────────────────
    try:
        mem_prompt = f"{context}\n\n---\n{MEMORY_REVIEW_PROMPT}"
        response = llm.generate(system_instruction=SYSTEM_PROMPT, prompt=mem_prompt)

        if response and "nothing" not in response.lower()[:30]:
            for line in response.strip().splitlines():
                parsed = _parse_action(line)
                if not parsed:
                    continue
                tool_name, kwargs = parsed
                if tool_name != "memory":
                    continue
                result = registry._execute_memory(kwargs)
                result_data = json.loads(result)
                if result_data.get("success"):
                    target = kwargs.get("target", "memory")
                    content_preview = (kwargs.get("content") or "")[:40]
                    actions_taken.append(f"Memory updated ({target}: {content_preview}...)")
    except Exception as e:
        logger.debug("Memory review failed: %s", e)

    # ── 2. Skill review (only if execution_log has steps) ────────────────────
    if execution_log:
        try:
            skill_prompt = f"{context}\n\n---\n{SKILL_REVIEW_PROMPT}"
            response = llm.generate(system_instruction=SYSTEM_PROMPT, prompt=skill_prompt)

            if response and "nothing" not in response.lower()[:30]:
                parsed = _parse_action(response)
                if parsed:
                    tool_name, kwargs = parsed
                    if tool_name == "save_recent_workflow_as_tool":
                        desc = kwargs.get("task_description", "")
                        result = registry._save_recent_workflow(desc, execution_log)
                        if "Success" in result:
                            skill_name = re.search(r"'(.+?)'", result)
                            name = skill_name.group(1) if skill_name else desc[:30]
                            actions_taken.append(f"Skill '{name}' created")
        except Exception as e:
            logger.debug("Skill review failed: %s", e)

    # ── 3. Notify ─────────────────────────────────────────────────────────────
    if actions_taken and callback:
        summary = " · ".join(actions_taken)
        try:
            callback(f"💾 Self-improvement review: {summary}")
        except Exception as e:
            logger.debug("Review callback failed: %s", e)


def spawn_background_review(
    llm,
    memory_store,
    registry,
    user_input: str,
    assistant_response: str,
    history: List[Dict],
    execution_log: List[Dict],
    callback: Optional[Callable[[str], None]] = None,
) -> threading.Thread:
    """Spawns daemon thread for background review. Returns the thread."""
    thread = threading.Thread(
        target=run_background_review,
        args=(llm, memory_store, registry, user_input, assistant_response,
              history, execution_log, callback),
        daemon=True,
    )
    thread.start()
    return thread
