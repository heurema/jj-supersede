"""Output formatting: terminal table and JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from .score import SupersessionCandidate


def format_table(candidates: list[SupersessionCandidate]) -> str:
    """Format candidates as a terminal table."""
    if not candidates:
        return "No superseded functions detected."

    header = f"{'Score':>5}  {'Function':<40}  {'File':<50}  {'Old→New'}"
    sep = "─" * len(header)
    lines = [sep, header, sep]

    for c in candidates:
        score_str = f"{c.score:.2f}"
        fn_str = c.function_name[:40]
        file_str = f"{c.path}:{c.old_line}"[:50]
        commits = f"{c.old_commit}→{c.new_commit}"
        lines.append(f"{score_str:>5}  {fn_str:<40}  {file_str:<50}  {commits}")

    lines.append(sep)
    lines.append(f"\n{len(candidates)} superseded function(s) detected.")
    return "\n".join(lines)


def format_json(candidates: list[SupersessionCandidate]) -> str:
    """Format candidates as JSON."""
    items = []
    for c in candidates:
        d = asdict(c)
        d["score"] = round(d["score"], 4)
        d["components"]["function_overlap"] = round(d["components"]["function_overlap"], 4)
        d["components"]["author_match"] = round(d["components"]["author_match"], 4)
        d["components"]["recency"] = round(d["components"]["recency"], 4)
        items.append(d)
    return json.dumps({"superseded": items, "count": len(items)}, indent=2)
