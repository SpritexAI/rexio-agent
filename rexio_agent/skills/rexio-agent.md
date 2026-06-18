---
name: rexio-agent
description: RexiO Agent architecture, file paths, commands, and configuration — self-knowledge for self-repair
---

## RexiO Agent — Self Knowledge

RexiO Agent is an open-source, self-improving AI agent framework built by SpritEX. It uses a Python backend (ReAct loop) and a React/TypeScript web dashboard.

### Installation Layout

```
~/.rexio/                        ← global config dir (GLOBAL_REXIO_DIR)
├── config.json                  ← model provider, API keys, bot tokens
├── rexio_agent.db               ← SQLite database (messages, skills, memory)
├── core/                        ← source code (git repo)
│   ├── run_agent.py             ← FastAPI server entry point
│   ├── cli.py                   ← CLI entry point (rexio command)
│   ├── rexio_agent/
│   │   ├── SOUL.md              ← agent persona (loaded each request)
│   │   ├── core/
│   │   │   ├── loop.py          ← ReAct agent loop (AgentSession)
│   │   │   ├── llm.py           ← LLM client (OpenRouter/Gemini/OpenAI)
│   │   │   ├── memory_store.py  ← MEMORY.md + USER.md file-backed memory
│   │   │   ├── background_review.py ← post-turn self-improvement review
│   │   │   ├── skills_compiler.py   ← compile execution log → Python skill
│   │   │   └── config.py        ← paths and config loader
│   │   ├── db/
│   │   │   ├── connection.py    ← SQLite helpers (save_message, get_messages...)
│   │   │   ├── schema.sql       ← DB schema
│   │   │   └── seed_skills.py   ← default markdown skills seeder
│   │   ├── gateway/
│   │   │   └── telegram.py      ← Telegram bot gateway
│   │   ├── skills/              ← markdown skill files (*.md)
│   │   └── tools/
│   │       ├── registry.py      ← ToolRegistry (all tools + memory tool)
│   │       ├── web_tools.py     ← search_web (DuckDuckGo)
│   │       ├── file_tools.py    ← read_file, write_file, list_directory
│   │       └── executor.py      ← execute_python_code
│   ├── web/                     ← React frontend (Vite + Tailwind)
│   │   └── dist/                ← built frontend (served by FastAPI)
│   └── .venv/                   ← Python virtualenv
└── memories/                    ← persistent memory files
    ├── MEMORY.md                ← agent notes (env facts, conventions)
    └── USER.md                  ← user profile (name, prefs, habits)
```

### Key Paths

| Path | Purpose |
|---|---|
| `~/.rexio/config.json` | API keys, model config, bot tokens |
| `~/.rexio/rexio_agent.db` | SQLite DB (messages, skills, step logs) |
| `~/.rexio/core/rexio_agent/SOUL.md` | Persona file — edit to change behavior |
| `~/.rexio/core/rexio_agent/skills/*.md` | Markdown skills (auto-loaded) |
| `~/.rexio/memories/MEMORY.md` | Agent persistent notes |
| `~/.rexio/memories/USER.md` | User persistent profile |
| `/etc/systemd/system/rexio.service` | System service file (VPS) |
| `~/.config/systemd/user/rexio.service` | User service file (local) |

### CLI Commands

```bash
rexio                    # Launch interactive CLI
rexio update             # git pull + pip install + npm build + service restart
rexio gateway install    # Install system-level service (sudo, VPS)
rexio server             # Start FastAPI backend only
rexio setup              # Re-run setup wizard
```

### Service Commands

```bash
# System-level (VPS — stays alive after SSH disconnect)
sudo systemctl status rexio
sudo systemctl restart rexio
sudo systemctl stop rexio
journalctl -u rexio -f        # live logs

# User-level (local desktop)
systemctl --user status rexio
systemctl --user restart rexio
```

### API Endpoints

```
GET  /api/status                          → backend health + model name
GET  /api/conversations                   → all chat sessions
GET  /api/conversations/{id}/messages     → messages + steps for session
POST /api/chat/stream                     → SSE stream (main chat endpoint)
GET  /api/skills                          → all compiled skills
GET  /api/skills/pending                  → pending approval
POST /api/skills/{name}/approve           → approve compiled skill
POST /api/skills/{name}/reject            → reject compiled skill
GET  /api/markdown-skills                 → all markdown skills
POST /api/markdown-skills                 → create markdown skill
DELETE /api/markdown-skills/{name}        → delete markdown skill
```

### Configuration (config.json)

```json
{
  "MODEL_PROVIDER": "openrouter",
  "MODEL_NAME": "openrouter/model-name",
  "OPENAI_API_KEY": "sk-or-...",
  "API_BASE_URL": "https://openrouter.ai/api/v1",
  "TELEGRAM_BOT_TOKEN": "...",
  "TELEGRAM_CHAT_ID": "...",
  "PORT": "51730"
}
```

Supported `MODEL_PROVIDER` values: `openrouter`, `openai`, `gemini`, `custom`

### ReAct Loop

Every user message goes through:
1. Load conversation history from DB
2. Build system prompt (SOUL.md + memory snapshot + markdown skills + tool definitions)
3. ReAct loop: Thought → Action → Observation (repeat up to 10 steps)
4. Stream final answer token by token
5. Save message + execution steps to DB
6. Spawn background review thread (memory + skill self-improvement)

### Available Tools (built-in)

| Tool | Description |
|---|---|
| `search_web(query)` | DuckDuckGo web search |
| `read_file(path)` | Read file contents |
| `write_file(path, content)` | Write file |
| `list_directory(path)` | List directory |
| `execute_python_code(code)` | Run Python in sandbox |
| `memory(action, target, content)` | Save/update/remove persistent memory |
| `save_recent_workflow_as_tool(task_description)` | Compile workflow into reusable skill |

### Updating RexiO

```bash
rexio update
```

This: pulls latest from GitHub → reinstalls dependencies → rebuilds web frontend → restarts service.

Manual update:
```bash
cd ~/.rexio/core
git pull origin main
.venv/bin/pip install -e .
cd web && npm run build
sudo systemctl restart rexio   # or: systemctl --user restart rexio
```