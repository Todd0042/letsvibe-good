#!/bin/sh
# Starts Fair Share. Needs Python 3.9 or newer.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then exec python3 fairshare.py "$@"; fi
if command -v python >/dev/null 2>&1; then exec python fairshare.py "$@"; fi
echo "Fair Share needs Python 3.9 or newer: https://www.python.org/downloads/"
exit 1
