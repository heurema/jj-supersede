#!/usr/bin/env bash
# SessionStart hook for Claude Code
# Runs jj-supersede context and injects warnings into agent prompt.
#
# Install in settings.json:
#   "SessionStart": [{
#     "matcher": "",
#     "hooks": [{"type": "command", "command": "bash /path/to/session-start.sh", "timeout": 15}]
#   }]

set -euo pipefail

# Skip if not a jj repo
[ -d ".jj" ] || exit 0

# Skip if jj-supersede not installed
command -v jj-supersede >/dev/null 2>&1 || exit 0

# Run context scan (threshold 0.7, silent on errors)
CONTEXT=$(jj-supersede context 2>/dev/null) || exit 0

# No superseded code found — nothing to inject
[ -z "$CONTEXT" ] && exit 0

# Escape for JSON
ESCAPED=$(python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" <<< "$CONTEXT")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": $ESCAPED
  }
}
EOF
