# Agent Instructions

## Documentation Safety

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

## Completing Planned Work

Always tick off To-Dos in the plan as they are completed. If new tasks are identified and required during building then add them as new To-Dos and tick them off once completed. Always update the `docs/decision_log.md` when new decisions are decided. 