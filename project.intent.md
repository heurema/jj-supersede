# jj-supersede — Project Intent

## Goal

Detect function-level code supersession in jj-tracked repositories by combining jj predecessor chains with tree-sitter AST analysis, so that "ghost solutions" — code that is semantically replaced but structurally present — can be surfaced, scored, and fed into automated cleanup pipelines.

## Core Capabilities

- Walk jj predecessor chains (`jj evolog --no-graph -T 'json(self)'`) to reconstruct the full evolution history of any change
- Extract function boundaries using py-tree-sitter `changed_ranges()` + language-specific `function_definition` queries for Python, Rust, and JavaScript
- Compute a composite supersession score per function pair: `score(A->B) = w1*function_overlap + w2*same_author + w3*recency_factor`, where w1=0.5, w2=0.25, w3=0.25
- `detect <change-id>` — show superseded functions in the evolution history of a single change
- `scan` — scan all recent changes in the repository for ghost solutions
- `report --json` — emit machine-readable JSON output for downstream consumption by signum's CONTRACT phase

## Non-Goals

- NOT a Rust-native tool using jj-lib directly — the jj-lib Rust API is unstable and not published on crates.io
- NOT a general dead code finder — dead code detection is handled by Layer 1 tools (knip, vulture, treeshake)
- NOT an embedding/ML-based detector in v0.1 — UniXcoder embedding distance deferred to Phase 6
- NOT a call graph analyzer in v0.1 — caller migration rate analysis deferred to Phase 6
- NOT a git-based tool — predecessor chains are structurally impossible to replicate from git

## Success Criteria

- `jj-supersede scan --json` produces valid JSON output consumable by signum
- Function extraction handles Python, Rust, and JavaScript grammars
- Supersession score threshold of 0.7 correctly flags known ghost solutions (to be tuned)
- `report --json` integrates with signum CONTRACT phase to generate `cleanupObligations`
- Test suite passes via pytest

## Personas

- **Developer (interactive)**: uses `detect` / `scan` to inspect superseded functions before submitting
- **AI Agent (session-start hook)**: receives `scan --json` output injected into context via Phase 5 hook
- **signum contractor (pipeline)**: reads `report --json` during CONTRACT phase to auto-generate `cleanupObligations`
