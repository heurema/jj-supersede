"""Tests for supersession scoring."""

from datetime import datetime, timezone

from jj_supersede.evolution import Author, CommitEntry
from jj_supersede.functions import FunctionDef, FunctionDiff
from jj_supersede.score import (
    compute_author_match,
    compute_function_overlap,
    compute_recency,
    filter_candidates,
    score_pair,
)


def _make_author(name: str = "Alice", email: str = "alice@example.com", ts: str = "2026-03-20T12:00:00+00:00") -> Author:
    return Author(name=name, email=email, timestamp=datetime.fromisoformat(ts))


def _make_entry(
    commit_id: str = "abc123",
    change_id: str = "change1",
    author: Author | None = None,
    committer: Author | None = None,
    description: str = "test",
) -> CommitEntry:
    if author is None:
        author = _make_author()
    if committer is None:
        committer = author
    return CommitEntry(
        commit_id=commit_id,
        change_id=change_id,
        parents=[],
        description=description,
        author=author,
        committer=committer,
        operation_description="test op",
        operation_time=datetime.now(timezone.utc),
        is_snapshot=False,
    )


def _make_fn(name: str, body: str = "pass") -> FunctionDef:
    body_bytes = body.encode("utf-8")
    return FunctionDef(
        name=name,
        start_byte=0,
        end_byte=len(body_bytes),
        start_line=1,
        end_line=1,
        body_hash=hash(body_bytes),
    )


def test_author_match_same():
    a = _make_author()
    b = _make_author()
    pred = _make_entry(author=a)
    succ = _make_entry(author=b)
    assert compute_author_match(pred, succ) == 1.0


def test_author_match_different():
    a = _make_author(name="Alice", email="alice@example.com")
    b = _make_author(name="Bob", email="bob@example.com")
    pred = _make_entry(author=a)
    succ = _make_entry(author=b)
    assert compute_author_match(pred, succ) == 0.0


def test_recency_recent():
    now = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    entry = _make_entry(committer=_make_author(ts="2026-03-20T10:00:00+00:00"))
    score = compute_recency(entry, now)
    assert score > 0.9


def test_recency_old():
    now = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    entry = _make_entry(committer=_make_author(ts="2025-01-01T00:00:00+00:00"))
    score = compute_recency(entry, now)
    assert score == 0.0


def test_function_overlap_all_modified():
    diff = FunctionDiff(
        path="test.py",
        added=[],
        removed=[],
        modified=[(_make_fn("a"), _make_fn("a", "new")), (_make_fn("b"), _make_fn("b", "new"))],
    )
    assert compute_function_overlap(diff) == 1.0


def test_function_overlap_mixed():
    diff = FunctionDiff(
        path="test.py",
        added=[_make_fn("c")],
        removed=[_make_fn("d")],
        modified=[(_make_fn("a"), _make_fn("a", "new"))],
    )
    overlap = compute_function_overlap(diff)
    assert 0.5 < overlap < 0.8  # 2/3 = 0.667


def test_function_overlap_empty():
    diff = FunctionDiff(path="test.py", added=[], removed=[], modified=[])
    assert compute_function_overlap(diff) == 0.0


def test_score_pair_produces_candidates():
    now = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    pred = _make_entry(commit_id="old123456789", committer=_make_author(ts="2026-03-19T12:00:00+00:00"))
    succ = _make_entry(commit_id="new123456789", committer=_make_author(ts="2026-03-20T12:00:00+00:00"))
    diff = FunctionDiff(
        path="src/auth.py",
        added=[],
        removed=[_make_fn("old_login")],
        modified=[(_make_fn("validate"), _make_fn("validate", "new_validate"))],
    )
    candidates = score_pair(pred, succ, diff, now)
    assert len(candidates) == 2
    names = {c.function_name for c in candidates}
    assert "validate" in names
    assert "old_login" in names
    for c in candidates:
        assert c.score > 0


def test_filter_candidates_deduplicates():
    from jj_supersede.score import ScoreComponents, SupersessionCandidate

    c1 = SupersessionCandidate(
        path="a.py", function_name="foo", old_commit="old1", new_commit="new1",
        change_id="c1", score=0.6, components=ScoreComponents(0.5, 1.0, 0.5),
        old_line=1, new_line=2,
    )
    c2 = SupersessionCandidate(
        path="a.py", function_name="foo", old_commit="old2", new_commit="new2",
        change_id="c1", score=0.8, components=ScoreComponents(0.7, 1.0, 0.5),
        old_line=1, new_line=2,
    )
    c3 = SupersessionCandidate(
        path="a.py", function_name="bar", old_commit="old1", new_commit="new1",
        change_id="c1", score=0.3, components=ScoreComponents(0.2, 0.0, 0.5),
        old_line=5, new_line=6,
    )
    result = filter_candidates([c1, c2, c3], threshold=0.5)
    assert len(result) == 1  # c3 below threshold, c1/c2 deduped to c2
    assert result[0].score == 0.8
