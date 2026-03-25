```
       _   _                                                __
      (_) (_)     _______  ______  ___  _____________  ____/ /__
     / / / /_____/ ___/ / / / __ \/ _ \/ ___/ ___/ _ \/ __  / _ \
    / / / /_____(__  ) /_/ / /_/ /  __/ /  (__  )  __/ /_/ /  __/
 __/ /_/ /     /____/\__,_/ .___/\___/_/  /____/\___/\__,_/\___/
/___/___/                /_/
```

**Detect function-level code supersession in jj repositories.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Find ghost solutions left behind by AI agents — code that compiles, has tests, but is no longer the intended solution.

---

## Install

```
uv tool install jj-supersede
```

Requires jj installed and a jj-managed repository.

## Usage

```bash
# Show superseded functions in a single change's history
jj-supersede detect <change-id>

# Scan recent mutable changes
jj-supersede scan

# JSON output for pipelines
jj-supersede report --json
```

### Options

```
-t, --threshold   Minimum score (0-1, default: 0.5)
-n, --limit       Max changes to scan (default: 20)
-r, --revset      Revset to scan (default: mutable())
-C, --cwd         Repository path
--json             JSON output (detect/scan)
```

## How it works

```
jj evolog (JSON) → changed files → tree-sitter function extraction → score
```

For each predecessor-successor pair in a change's evolution:

1. Parse `jj evolog` JSON to get the predecessor chain
2. Diff changed files between versions
3. Extract function definitions via tree-sitter (qualified names: `Class.method`)
4. Score each modified/removed function:

```
score = 0.50 × function_overlap
      + 0.25 × same_author
      + 0.25 × recency
```

Functions above the threshold are reported as supersession candidates.

## Supported languages

Python, Rust, JavaScript, TypeScript (JSX/TSX).

## Example output

```
─────────────────────────────────────────────────────────────────────
Score  Function                                  File                 Old→New
─────────────────────────────────────────────────────────────────────
 0.85  login                                     src/auth.py:10       abc123→def456
 0.72  validate_token                            src/auth.py:30       abc123→def456
─────────────────────────────────────────────────────────────────────

2 superseded function(s) detected.
```

## Integration

### signum (v4.15.0+)

[signum](https://github.com/heurema/signum)'s contractor automatically calls `jj-supersede report --json` during the CONTRACT phase in jj repositories. Superseded functions become `removals` (type: `function`) and non-blocking `cleanupObligations` (action: `remove_code`).

```
jj-supersede report --json → signum CONTRACT → cleanupObligations → EXECUTE → RECONCILE
```

No configuration needed — the integration is optional and silently skipped if jj-supersede is not installed.

### Claude Code session-start hook

The `context` command outputs warnings for agent injection:

```bash
jj-supersede context
```

A [session-start hook](hooks/session-start.sh) wraps this for Claude Code's SessionStart event, injecting ghost solution warnings into the agent's system prompt at session start.

## Development

```bash
uv sync
uv run pytest
```
