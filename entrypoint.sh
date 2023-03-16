#!/usr/bin/env sh

# The Docker App Container's entry point.
# This is a script used by the project's to setup the app containers and databases upon running.

set -e

# Execute the given or default command replacing the pid 1:
if [ $# -gt 0 ]; then
    echo "== Executing custom command: $* ..."
    exec "$@"
else
    echo "== Started cron mode ..."
    exec python main.py
fi
