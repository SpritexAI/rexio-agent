-- SQLite schema for RexiO Agent

-- Conversations table to track interactive sessions
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    platform TEXT NOT NULL,         -- 'cli', 'telegram', 'discord', 'web'
    channel_id TEXT NOT NULL,       -- Chat ID or terminal session ID
    summary TEXT
);

-- Messages table to track individual chats
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,             -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Skills table for dynamically learned behaviors
CREATE TABLE IF NOT EXISTS skills (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    code TEXT NOT NULL,             -- Python code content for the skill
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled tasks (cron / background interval tasks)
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,         -- Cron expression (e.g. "*/5 * * * *")
    prompt TEXT NOT NULL,           -- Prompt to execute
    platform TEXT NOT NULL,         -- Notification target platform
    channel_id TEXT NOT NULL,       -- Target channel ID
    last_run TIMESTAMP,
    status TEXT DEFAULT 'active',   -- 'active', 'paused'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic memories / general key-value facts
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,       -- E.g. 'user_name', 'project_preferences'
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
