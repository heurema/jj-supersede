"""Integration test: create a jj repo, make code changes, detect supersession."""

import json
import os
import shutil
import subprocess
import tempfile

import pytest

from jj_supersede.cli import _analyze_chain
from jj_supersede.evolution import get_evolog, get_recent_changes


pytestmark = pytest.mark.skipif(
    shutil.which("jj") is None, reason="jj not installed"
)


@pytest.fixture
def jj_repo(tmp_path):
    """Create a temporary jj repo with Python code and amendments."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    env = os.environ.copy()
    env["JJ_USER"] = "Test User"
    env["JJ_EMAIL"] = "test@example.com"

    def jj(*args):
        result = subprocess.run(
            ["jj", *args], capture_output=True, text=True, cwd=str(repo), env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"jj {' '.join(args)}: {result.stderr}")
        return result.stdout

    # Init repo
    jj("git", "init")

    # V1: write initial Python file
    auth_py = repo / "auth.py"
    auth_py.write_text('''\
def login(username, password):
    """Basic login."""
    if username == "admin" and password == "secret":
        return True
    return False

def logout(session_id):
    """End session."""
    print(f"Logging out {session_id}")
    return True

def validate_token(token):
    """Check if token is valid."""
    return len(token) > 10
''')

    # Commit v1
    jj("commit", "-m", "feat: initial auth module")

    # Get the change ID of the working copy (this is where we'll amend)
    change_id_raw = jj("log", "--no-graph", "-T", "change_id", "-r", "@-")
    change_id = change_id_raw.strip()

    # V2: amend with significant changes to the committed change
    auth_py.write_text('''\
def login(username, password):
    """JWT-based login with hashing."""
    import hashlib
    hashed = hashlib.sha256(password.encode()).hexdigest()
    # New implementation: check against database
    return {"token": f"jwt_{username}_{hashed[:8]}", "expires": 3600}

def logout(session_id):
    """End session."""
    print(f"Logging out {session_id}")
    return True

def validate_token(token):
    """JWT validation with expiry check."""
    if not token.startswith("jwt_"):
        return False
    parts = token.split("_")
    return len(parts) >= 3
''')

    # Squash the working copy into the previous commit (creates a new version)
    jj("squash", "--into", change_id[:8])

    return str(repo), change_id


def test_evolog_has_predecessors(jj_repo):
    repo_path, change_id = jj_repo
    chain = get_evolog(change_id[:8], cwd=repo_path)
    # Should have at least 2 versions (original + amended)
    assert len(chain.entries) >= 2
    assert chain.current is not None
    assert len(chain.predecessors) >= 1


def test_detect_finds_modified_functions(jj_repo):
    repo_path, change_id = jj_repo
    candidates = _analyze_chain(change_id[:8], cwd=repo_path, threshold=0.0)
    # login and validate_token were modified
    fn_names = {c.function_name for c in candidates}
    assert "login" in fn_names or "validate_token" in fn_names


def test_detect_json_output(jj_repo):
    repo_path, change_id = jj_repo
    candidates = _analyze_chain(change_id[:8], cwd=repo_path, threshold=0.0)
    from jj_supersede.output import format_json

    output = format_json(candidates)
    data = json.loads(output)
    assert "superseded" in data
    assert "count" in data
    assert data["count"] > 0


def test_scan_finds_changes(jj_repo):
    repo_path, _ = jj_repo
    change_ids = get_recent_changes(cwd=repo_path, limit=10)
    assert len(change_ids) > 0
