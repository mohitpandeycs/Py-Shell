#!/bin/sh
#
# Use this script to run your program LOCALLY.
#
set -e # Exit early if any commands fail
#
# - Edit this to change how your program runs locally

SCRIPT_DIR="$(dirname "$0")"
PYTHONSAFEPATH=1 PYTHONPATH="$SCRIPT_DIR" exec uv run \
  --project "$SCRIPT_DIR" \
  --quiet \
  -m app.main \
  "$@"
