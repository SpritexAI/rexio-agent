---
name: planning
description: Write clear implementation plans before coding
---

## Planning Mode

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
