#!/usr/bin/env bash
set -euo pipefail

if [ ! -d "src" ]; then
    echo "src/ does not exist; nothing to check."
    exit 0
fi

VIOLATIONS=$(grep -rEn '^\s*#' src/ \
    | grep -vE ':[0-9]+:#!' \
    | grep -vE ':[0-9]+:# -\*- coding' \
    | grep -vE 'noqa' \
    | grep -vE 'type: ignore' \
    || true)

if [ -n "$VIOLATIONS" ]; then
    echo "Comment violation: code in src/ contains comments."
    echo ""
    echo "Offending lines:"
    echo "$VIOLATIONS"
    echo ""
    echo "Fix: rename a variable, extract a function, add a test, or move the explanation to the commit message."
    exit 1
fi

echo "No-comments check passed."
