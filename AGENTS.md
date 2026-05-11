# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Update Planning Docs

**Update planning docs as you refine and complete tasks**

When working on a sprint or series of tasks:
- Tick of tasks as you complete them.
- Add any silent tasks that were required but not outlined in the plan.
- Add a short summary of the work completed to the planning doc for easy review

## 6. Documentation Safety

Never write machine-specific absolute paths into committed documentation, code comments, examples, config templates, or generated markdown.

Do not include paths like:

- `/Users/<name>/...`
- `/home/<name>/...`
- `/private/var/...`
- `C:\Users\<name>\...`
- Local OneDrive, Dropbox, iCloud, Desktop, Downloads, or Documents paths

Use repo-relative paths instead.

Good examples:

- `data/raw/input.csv`
- `docs/project-plan.md`
- `scripts/load_data.py`
- `${PROJECT_ROOT}/data/raw/input.csv`
- `<repo-root>/data/raw/input.csv`

Bad examples:

- `/Users/dan/project/data/raw/input.csv`
- `/Users/dan/Desktop/project/docs/output.md`
- `C:\Users\Dan\Documents\repo\data\raw\input.csv`

When documenting commands, assume the user is running from the repository root unless otherwise stated.

If an absolute path appears in source material, rewrite it before saving:

- Replace the repo root absolute path with `<repo-root>/`
- Replace user home directories with `~` only when describing local setup
- Prefer relative paths for files inside this repository

Before finalizing any documentation change, scan changed markdown, YAML, JSON, SQL, Python, R, and shell files for local absolute paths.

## 7. Completing Planned Work

Always tick off To-Dos in the plan as they are completed. If new tasks are identified and required during building then add them as new To-Dos and tick them off once completed. Always update the `docs/decision_log.md` when new decisions are decided. 