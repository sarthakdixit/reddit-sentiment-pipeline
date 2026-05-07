#!/usr/bin/env bash
set -euo pipefail

BANNED_IMPORTS='^(import|from) (azure|praw|psycopg2|sqlalchemy|boto3|google\.cloud|requests|httpx|urllib3|pyodbc|pymongo|redis)'

if [ ! -d "src/core" ]; then
    echo "src/core/ does not exist; nothing to check."
    exit 0
fi

VIOLATIONS=$(grep -rE "$BANNED_IMPORTS" src/core/ || true)

if [ -n "$VIOLATIONS" ]; then
    echo "Architecture boundary violation: src/core/ imports infrastructure libraries."
    echo ""
    echo "Offending lines:"
    echo "$VIOLATIONS"
    echo ""
    echo "Fix: move the import to src/adapters/ and define a Protocol in src/core/ports.py."
    exit 1
fi

echo "Architecture boundary check passed."
