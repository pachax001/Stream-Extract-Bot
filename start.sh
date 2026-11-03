#!/bin/sh
set -e

# Fetch the configured repository and branch on every container/process startup.
# A Git or network failure must not prevent the existing bot from starting.
if ! python3 update.py; then
    echo "[startup] Auto-update failed; starting existing bot code." >&2
fi

exec python3 main.py
