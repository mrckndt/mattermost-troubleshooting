---
name: search-tickets
description: Search across all past tickets for a keyword, error string, or symptom. Searches analysis logs and raw ticket files, groups results by ticket ID with context snippets.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

If no argument is provided, ask for a search term before proceeding.

## Search

Run the following searches in parallel:

1. Analysis logs:
```
rg -l "$ARGUMENTS" "$PROJECT_ROOT/tickets/" -g "analysis*.md"
```
2. Raw ticket files:
```
rg -l "$ARGUMENTS" "$PROJECT_ROOT/tickets/"
```

For each matching file, get a context snippet:
```
rg -n "$ARGUMENTS" <file> | head -5
```

## Output

Group results by ticket ID. For each ticket with matches:

- **`tickets/<ID>/`** - `<one-line characterization from analysis.md reported symptom, or inferred from filenames>`
  - `<file>:<line>: <matched line snippet>` (up to 3 snippets per ticket)

Order by match density (most matches first). If no matches found, say so explicitly.
