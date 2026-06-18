# RexiO Agent ☤

RexiO Agent is a self-improving, persistent AI agent framework. It uses a hybrid Python and TypeScript architecture, allowing it to perform backend execution, run cron routines, learn skills dynamically, and stream updates to chat clients or a web-based dashboard.

## Features

- **Core ReAct Loop:** Built-in planning, acting, and reflection cycles.
- **SQLite Persistence:** Keeps tracking of chat sessions, system states, schedules, and semantic memory.
- **Built-in Tools:** Integrated file management, web search, and a timed Python sandbox executor.
- **Self-Improving Learning Loop:** Ability to compile new dynamic tools from successful runs and execute them at runtime.
- **Interactive UI:** A real CLI client and an upcoming FastAPI-based React + Tailwind CSS dashboard.

## Installation

### 1. Requirements
- Python 3.11+
- `uv` (recommended for faster package dependency handling)

### 2. Quick Setup
Clone the repository, configure the environment, and install dependencies.

```bash
# Copy and configure environment variables
cp .env.example .env

# Install dependencies
uv pip install -e .
# Or standard pip install:
pip install -r requirements.txt
```

### 3. Run CLI
Launch the interactive session:
```bash
python cli.py
```

## Architecture

Please refer to the architecture plan in [.agents/skills/](../../.agents/skills/) (or local config directories) for detailed UML and technical diagrams.

## License

MIT
