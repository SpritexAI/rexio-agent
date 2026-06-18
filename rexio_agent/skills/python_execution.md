---
name: python_execution
description: Safe Python code execution patterns
---

## Python Code Execution

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
