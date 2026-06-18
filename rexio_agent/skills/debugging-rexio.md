---
name: debugging-rexio
description: Debug and fix common RexiO Agent issues — service, API, Telegram, memory, skills
---

## Debugging RexiO Agent

Use this skill when RexiO is broken, not responding, or behaving unexpectedly.

### Step 1 — Identify where it broke

```bash
# Is the service running?
sudo systemctl status rexio          # system service
systemctl --user status rexio        # user service

# Is the API responding?
curl http://localhost:51730/api/status

# Recent logs
journalctl -u rexio -n 50 --no-pager           # system service
journalctl --user -u rexio -n 50 --no-pager    # user service

# Log files (if service uses file logging)
tail -50 ~/.rexio/rexio.log
tail -50 ~/.rexio/rexio.error.log
```

### Common Issues & Fixes

#### Service not starting — "Address already in use"
```bash
# Find what's using the port
lsof -i :51730
kill <PID>
sudo systemctl restart rexio
```

#### Service not starting — Python import error
```bash
# Reinstall dependencies
cd ~/.rexio/core
.venv/bin/pip install -e .
sudo systemctl restart rexio
```

#### Telegram not responding
1. Check service is running: `sudo systemctl status rexio`
2. Check bot token in config: `cat ~/.rexio/config.json | grep TELEGRAM`
3. Check logs: `journalctl -u rexio -n 30`
4. If service crashed, restart: `sudo systemctl restart rexio`

#### Web frontend not loading
```bash
# Rebuild frontend
cd ~/.rexio/core/web
npm install
npm run build
sudo systemctl restart rexio
```

#### Database errors
```bash
# Check DB exists
ls -la ~/.rexio/rexio_agent.db

# Re-run migrations (safe — CREATE IF NOT EXISTS)
cd ~/.rexio/core
.venv/bin/python -c "from rexio_agent.db.connection import init_db; init_db(); print('DB OK')"
```

#### Memory not loading
```bash
# Check memory files
ls -la ~/.rexio/memories/
cat ~/.rexio/memories/MEMORY.md
cat ~/.rexio/memories/USER.md
```

#### Skills not loading
```bash
# List skill files
ls ~/.rexio/core/rexio_agent/skills/

# Re-seed default skills
cd ~/.rexio/core
.venv/bin/python -m rexio_agent.db.seed_skills
```

#### Model errors (NoneType, empty choices)
- Check API key: `cat ~/.rexio/config.json | grep API_KEY`
- Try a different model in config.json (`MODEL_NAME`)
- Check OpenRouter status or switch provider

#### Config changes not taking effect
```bash
sudo systemctl restart rexio
```
Config is loaded at startup from `~/.rexio/config.json`.

### Full Reset (nuclear option)

```bash
# Stop service
sudo systemctl stop rexio

# Backup DB
cp ~/.rexio/rexio_agent.db ~/.rexio/rexio_agent.db.bak

# Pull latest code + reinstall
cd ~/.rexio/core
git pull origin main
.venv/bin/pip install -e .
cd web && npm run build

# Restart
sudo systemctl start rexio
```

### Editing Config

```bash
nano ~/.rexio/config.json
sudo systemctl restart rexio
```

### Editing Persona

```bash
nano ~/.rexio/core/rexio_agent/SOUL.md
# No restart needed — loaded fresh each request
```

### Adding a Markdown Skill

```bash
# Via file (auto-picked up on next request)
nano ~/.rexio/core/rexio_agent/skills/my_skill.md

# Via API
curl -X POST http://localhost:51730/api/markdown-skills \
  -H "Content-Type: application/json" \
  -d '{"name":"my_skill","description":"desc","content":"## Instructions\n..."}'
```

### Checking Service Type

```bash
# Which service is active?
sudo systemctl is-active rexio        # system-level
systemctl --user is-active rexio      # user-level

# System service = survives SSH disconnect + VPS reboot (preferred for VPS)
# User service = stops when SSH session ends (use only on local desktop)
```

### Verification After Fix

```bash
curl http://localhost:51730/api/status
# Expected: {"status":"online","model":"..."}
```