"""Parse jj evolog JSON output into predecessor chains."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Author:
    name: str
    email: str
    timestamp: datetime

    @classmethod
    def from_json(cls, data: dict) -> Author:
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass(frozen=True)
class CommitEntry:
    commit_id: str
    change_id: str
    parents: list[str]
    description: str
    author: Author
    committer: Author
    operation_description: str
    operation_time: datetime
    is_snapshot: bool

    @classmethod
    def from_json(cls, data: dict) -> CommitEntry:
        commit = data["commit"]
        op = data["operation"]
        return cls(
            commit_id=commit["commit_id"],
            change_id=commit["change_id"],
            parents=commit.get("parents", []),
            description=commit.get("description", "").strip(),
            author=Author.from_json(commit["author"]),
            committer=Author.from_json(commit["committer"]),
            operation_description=op.get("description", ""),
            operation_time=datetime.fromisoformat(op["time"]["start"]),
            is_snapshot=op.get("is_snapshot", False),
        )


@dataclass
class PredecessorChain:
    """Ordered list of commit versions for a single change ID (newest first)."""

    change_id: str
    entries: list[CommitEntry] = field(default_factory=list)

    @property
    def current(self) -> CommitEntry | None:
        return self.entries[0] if self.entries else None

    @property
    def predecessors(self) -> list[CommitEntry]:
        return self.entries[1:]

    def pairs(self) -> list[tuple[CommitEntry, CommitEntry]]:
        """Return (successor, predecessor) pairs for diffing."""
        return [(self.entries[i], self.entries[i + 1]) for i in range(len(self.entries) - 1)]


def run_jj(*args: str, cwd: str | None = None) -> str:
    result = subprocess.run(
        ["jj", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"jj {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def get_evolog(change_id: str, *, cwd: str | None = None, limit: int | None = None) -> PredecessorChain:
    """Get the evolution log for a change ID as a PredecessorChain."""
    args = ["evolog", "--no-graph", "-T", 'concat(json(self), "\\n")', "-r", change_id]
    if limit:
        args.extend(["-n", str(limit)])
    raw = run_jj(*args, cwd=cwd)

    entries = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        entries.append(CommitEntry.from_json(data))

    cid = entries[0].change_id if entries else change_id
    return PredecessorChain(change_id=cid, entries=entries)


def get_changed_files(from_commit: str, to_commit: str, *, cwd: str | None = None) -> list[str]:
    """Get list of files changed between two commits."""
    raw = run_jj("diff", "--from", from_commit, "--to", to_commit, "--name-only", cwd=cwd)
    return [f for f in raw.strip().splitlines() if f.strip()]


def get_file_content(commit_id: str, path: str, *, cwd: str | None = None) -> str | None:
    """Get file content at a specific commit. Returns None if file doesn't exist."""
    try:
        return run_jj("file", "show", path, "-r", commit_id, cwd=cwd)
    except RuntimeError:
        return None


def get_recent_changes(
    *, cwd: str | None = None, limit: int = 20, revset: str = "mutable()"
) -> list[str]:
    """Get recent change IDs from the repo."""
    raw = run_jj(
        "log",
        "--no-graph",
        "-T",
        'change_id ++ "\\n"',
        "-r",
        revset,
        "-n",
        str(limit),
        cwd=cwd,
    )
    return [cid.strip() for cid in raw.strip().splitlines() if cid.strip()]
