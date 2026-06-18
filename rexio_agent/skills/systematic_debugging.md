---
name: systematic_debugging
description: 4-phase root cause debugging: understand bugs before fixing
---

## Systematic Debugging

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
