"""Compute supersession scores for function pairs across predecessor chains."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .evolution import CommitEntry, PredecessorChain
from .functions import FunctionDiff


# Weights for composite score
W_FUNCTION_OVERLAP = 0.5
W_AUTHOR_MATCH = 0.25
W_RECENCY = 0.25

# Recency: changes within this many days get full recency score
RECENCY_WINDOW_DAYS = 14


@dataclass(frozen=True)
class SupersessionCandidate:
    """A function that may be superseded by another version."""

    path: str
    function_name: str
    old_commit: str
    new_commit: str
    change_id: str
    score: float
    components: ScoreComponents
    old_line: int
    new_line: int


@dataclass(frozen=True)
class ScoreComponents:
    function_overlap: float
    author_match: float
    recency: float


def compute_author_match(pred: CommitEntry, succ: CommitEntry) -> float:
    """1.0 if same author, 0.0 otherwise."""
    if pred.author.email and succ.author.email:
        return 1.0 if pred.author.email == succ.author.email else 0.0
    return 1.0 if pred.author.name == succ.author.name else 0.0


def compute_recency(entry: CommitEntry, now: datetime | None = None) -> float:
    """Score 0..1 based on how recent the change is. 1.0 = within RECENCY_WINDOW_DAYS."""
    if now is None:
        now = datetime.now(timezone.utc)

    ts = entry.committer.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_days = (now - ts).total_seconds() / 86400
    if age_days <= 0:
        return 1.0
    if age_days >= RECENCY_WINDOW_DAYS * 4:
        return 0.0
    return max(0.0, 1.0 - age_days / (RECENCY_WINDOW_DAYS * 4))


def compute_function_overlap(diff: FunctionDiff) -> float:
    """Score 0..1 based on ratio of modified+removed functions to total.

    High overlap = many functions changed/replaced = likely supersession.
    """
    total = len(diff.added) + len(diff.removed) + len(diff.modified)
    if total == 0:
        return 0.0
    superseding = len(diff.modified) + len(diff.removed)
    return superseding / total


def score_pair(
    pred: CommitEntry,
    succ: CommitEntry,
    diff: FunctionDiff,
    now: datetime | None = None,
) -> list[SupersessionCandidate]:
    """Score function supersession between a predecessor-successor pair."""
    candidates = []
    overlap = compute_function_overlap(diff)
    author = compute_author_match(pred, succ)
    recency = compute_recency(succ, now)

    composite = (
        W_FUNCTION_OVERLAP * overlap + W_AUTHOR_MATCH * author + W_RECENCY * recency
    )
    components = ScoreComponents(
        function_overlap=overlap, author_match=author, recency=recency
    )

    # Report modified functions (same name, different body = potential supersession)
    for old_fn, new_fn in diff.modified:
        candidates.append(
            SupersessionCandidate(
                path=diff.path,
                function_name=old_fn.name,
                old_commit=pred.commit_id[:12],
                new_commit=succ.commit_id[:12],
                change_id=pred.change_id,
                score=composite,
                components=components,
                old_line=old_fn.start_line,
                new_line=new_fn.start_line,
            )
        )

    # Report removed functions (present in old, gone in new = superseded & deleted)
    for fn in diff.removed:
        candidates.append(
            SupersessionCandidate(
                path=diff.path,
                function_name=fn.name,
                old_commit=pred.commit_id[:12],
                new_commit=succ.commit_id[:12],
                change_id=pred.change_id,
                score=composite,
                components=components,
                old_line=fn.start_line,
                new_line=0,
            )
        )

    return candidates


def filter_candidates(
    candidates: list[SupersessionCandidate], threshold: float = 0.5
) -> list[SupersessionCandidate]:
    """Filter candidates by score threshold and deduplicate by function name."""
    above = [c for c in candidates if c.score >= threshold]
    # Deduplicate: keep highest-scoring entry per (path, function_name)
    best: dict[tuple[str, str], SupersessionCandidate] = {}
    for c in above:
        key = (c.path, c.function_name)
        if key not in best or c.score > best[key].score:
            best[key] = c
    return sorted(best.values(), key=lambda c: c.score, reverse=True)
