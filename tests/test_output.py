"""Tests for output formatting."""

import json

from jj_supersede.output import format_json, format_table
from jj_supersede.score import ScoreComponents, SupersessionCandidate


def _sample_candidates() -> list[SupersessionCandidate]:
    return [
        SupersessionCandidate(
            path="src/auth.py",
            function_name="login",
            old_commit="abc123456789",
            new_commit="def456789012",
            change_id="change1",
            score=0.85,
            components=ScoreComponents(0.7, 1.0, 0.8),
            old_line=10,
            new_line=15,
        ),
        SupersessionCandidate(
            path="src/auth.py",
            function_name="validate_token",
            old_commit="abc123456789",
            new_commit="def456789012",
            change_id="change1",
            score=0.65,
            components=ScoreComponents(0.5, 1.0, 0.4),
            old_line=30,
            new_line=0,
        ),
    ]


def test_format_table():
    candidates = _sample_candidates()
    output = format_table(candidates)
    assert "login" in output
    assert "validate_token" in output
    assert "0.85" in output
    assert "2 superseded function(s)" in output


def test_format_table_empty():
    output = format_table([])
    assert "No superseded functions" in output


def test_format_json():
    candidates = _sample_candidates()
    output = format_json(candidates)
    data = json.loads(output)
    assert data["count"] == 2
    assert len(data["superseded"]) == 2
    assert data["superseded"][0]["function_name"] == "login"
    assert data["superseded"][0]["score"] == 0.85


def test_format_json_empty():
    output = format_json([])
    data = json.loads(output)
    assert data["count"] == 0
    assert data["superseded"] == []
