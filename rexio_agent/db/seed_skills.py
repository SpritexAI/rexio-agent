"""
Seed default markdown skills into the database.
Run once: python -m rexio_agent.db.seed_skills
"""
from rexio_agent.db.connection import init_db, save_markdown_skill

SKILLS = [
    {
        "name": "web_researcher",
        "description": "Web search best practices — cite sources, summarize findings",
        "content": """## Web Research Guidelines

When asked to research a topic:
1. Search with specific, targeted queries using `search_web`
2. Run multiple searches from different angles if needed
3. Always cite the source URL for every fact you present
4. Summarize findings in clear sections: **Overview**, **Key Facts**, **Sources**
5. If results are outdated, mention the date and note uncertainty
6. Never fabricate URLs or statistics — only report what you found

### Query tips
- Use quotes for exact phrases: `"machine learning" 2026`
- Add site restrictions mentally: prefer official docs, academic papers, reputable news
- For current events, include the year in the query
""",
    },
    {
        "name": "systematic_debugging",
        "description": "4-phase root cause debugging: understand bugs before fixing",
        "content": """## Systematic Debugging

**Iron Law: NEVER FIX WITHOUT FINDING ROOT CAUSE FIRST.**

### Phase 1 — Root Cause Investigation
- Read the full error message carefully
- Reproduce the bug consistently before attempting fixes
- Check recent changes (what changed right before this broke?)
- Trace the data flow from input to the point of failure

### Phase 2 — Pattern Analysis
- Find a working example to compare against
- Identify the exact difference between working and broken
- Check dependencies and environment differences

### Phase 3 — Hypothesis & Testing
- Form ONE hypothesis at a time
- Change ONE variable at a time
- Confirm the fix resolves the root cause, not just the symptom

### Phase 4 — Implementation
- Write a test that reproduces the bug first
- Implement the minimal fix
- Verify all tests pass

**If 3 consecutive fixes fail → stop and re-examine the architecture.**
""",
    },
    {
        "name": "planning",
        "description": "Write clear implementation plans before coding",
        "content": """## Planning Mode

When asked to plan or before starting a complex task:
1. **Do not write code yet** — plan first
2. Write a plan covering:
   - **Goal:** What we are trying to achieve
   - **Approach:** High-level strategy
   - **Steps:** Ordered, atomic steps (each 2-5 min of work)
   - **Files to change:** Exact file paths
   - **Risks:** What could go wrong
3. Each step must be a single atomic action
4. Present the plan and wait for confirmation before executing
5. Save plan to a file if it is complex (3+ steps)

### Good step example
> Edit `rexio_agent/core/loop.py` line 97: replace `get_skills()` with `get_active_skills()`

### Bad step example
> Update the skills system
""",
    },
    {
        "name": "code_output_format",
        "description": "Consistent code and output formatting rules",
        "content": """## Code & Output Formatting

### When writing code
- Use the language already present in the project
- Keep functions small and single-purpose
- No comments explaining WHAT — only WHY (non-obvious reasons)
- No unused imports or variables

### When presenting results
- Lead with the answer, then the reasoning
- Use markdown tables for structured data comparisons
- Use fenced code blocks with language tag for all code snippets
- Bold **key terms** on first use

### When answering questions
- One clear answer first, then elaboration if needed
- If uncertain, say so explicitly — do not guess confidently
- For multi-part questions, use numbered sections
""",
    },
    {
        "name": "file_operations",
        "description": "Safe file read/write patterns",
        "content": """## File Operations

### Before writing a file
- Always `read_file` first to understand current content
- Never overwrite without checking existing content
- For config files, preserve existing keys — only add/change what is needed

### Directory exploration
- Use `list_directory` to understand structure before reading individual files
- Start from the project root, go one level at a time

### Writing files
- Write complete file content — no partial writes
- Verify the write succeeded by reading back if critical

### Safety rules
- Never delete files unless explicitly instructed
- Never write to system paths (`/etc`, `/usr`, `/bin`)
- For scripts, prefer writing to the project directory
""",
    },
    {
        "name": "python_execution",
        "description": "Safe Python code execution patterns",
        "content": """## Python Code Execution

### Before executing
- Verify the code logic mentally before running
- For destructive operations (delete, overwrite), confirm with the user first
- Prefer pure-stdlib code when possible — no surprise imports

### Code style
- Use `print()` to return results — the output is the observation
- Handle exceptions and print useful error messages
- Keep scripts short and focused on one task

### After execution
- Check the output carefully before reporting results
- If output is empty, the script likely failed silently — add error handling
- For long-running scripts, add progress prints

### Sandboxing reminder
- Code runs in the agent process — no network isolation
- Avoid `os.system()` or `subprocess` unless necessary
- Never execute untrusted code received from web searches
""",
    },
]

def seed():
    init_db()
    for skill in SKILLS:
        save_markdown_skill(skill["name"], skill["description"], skill["content"])
        print(f"  ✓ {skill['name']}")
    print(f"\nSeeded {len(SKILLS)} default skills.")

if __name__ == "__main__":
    seed()
