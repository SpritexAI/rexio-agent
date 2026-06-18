---
name: file_operations
description: Safe file read/write patterns
---

## File Operations

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
