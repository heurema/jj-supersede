"""Tests for jj evolog parsing."""

import json
from datetime import datetime

from jj_supersede.evolution import CommitEntry, PredecessorChain


SAMPLE_EVOLOG_ENTRY = {
    "commit": {
        "commit_id": "c7dc758c2a952702a1a6a2a27adafc6cd7ab5794",
        "parents": ["98bda2ae2fe7d852c5f223682dd8dde76d6a985d"],
        "change_id": "yvxznttrutzlnxkoksquwrmpownwlyvm",
        "description": "feat: add authentication",
        "author": {
            "name": "Alice",
            "email": "alice@example.com",
            "timestamp": "2026-03-20T14:27:23+03:00",
        },
        "committer": {
            "name": "Alice",
            "email": "alice@example.com",
            "timestamp": "2026-03-20T14:27:23+03:00",
        },
    },
    "operation": {
        "id": "d3ef3268f75a",
        "parents": ["4427cc00030a"],
        "time": {
            "start": "2026-03-20T14:27:23.524+03:00",
            "end": "2026-03-20T14:27:23.544+03:00",
        },
        "description": "snapshot working copy",
        "hostname": "dev-machine",
        "username": "alice",
        "is_snapshot": True,
        "tags": {"args": "jj status"},
    },
}


def test_commit_entry_from_json():
    entry = CommitEntry.from_json(SAMPLE_EVOLOG_ENTRY)
    assert entry.commit_id == "c7dc758c2a952702a1a6a2a27adafc6cd7ab5794"
    assert entry.change_id == "yvxznttrutzlnxkoksquwrmpownwlyvm"
    assert entry.description == "feat: add authentication"
    assert entry.author.name == "Alice"
    assert entry.author.email == "alice@example.com"
    assert isinstance(entry.author.timestamp, datetime)
    assert entry.is_snapshot is True


def test_predecessor_chain():
    e1 = CommitEntry.from_json(SAMPLE_EVOLOG_ENTRY)

    e2_data = json.loads(json.dumps(SAMPLE_EVOLOG_ENTRY))
    e2_data["commit"]["commit_id"] = "aaa"
    e2_data["operation"]["is_snapshot"] = False
    e2 = CommitEntry.from_json(e2_data)

    e3_data = json.loads(json.dumps(SAMPLE_EVOLOG_ENTRY))
    e3_data["commit"]["commit_id"] = "bbb"
    e3_data["operation"]["is_snapshot"] = False
    e3 = CommitEntry.from_json(e3_data)

    chain = PredecessorChain(change_id="yvxz", entries=[e1, e2, e3])
    assert chain.current == e1
    assert chain.predecessors == [e2, e3]
    pairs = chain.pairs()
    assert len(pairs) == 2
    assert pairs[0] == (e1, e2)
    assert pairs[1] == (e2, e3)


def test_predecessor_chain_single():
    e = CommitEntry.from_json(SAMPLE_EVOLOG_ENTRY)
    chain = PredecessorChain(change_id="yvxz", entries=[e])
    assert chain.current == e
    assert chain.predecessors == []
    assert chain.pairs() == []


def test_predecessor_chain_empty():
    chain = PredecessorChain(change_id="yvxz", entries=[])
    assert chain.current is None
    assert chain.predecessors == []
    assert chain.pairs() == []
