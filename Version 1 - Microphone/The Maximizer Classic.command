#!/bin/bash
# The Maximizer Classic — Launcher
# Double-click this file in Finder to start the application.

# Find Python 3
PYTHON=""
for candidate in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display alert "Python 3 Not Found" message "Please install Python 3 from python.org or via Homebrew (brew install python3) to run The Maximizer Classic." as critical'
    exit 1
fi

# Check tkinter is available
if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
    osascript -e 'display alert "tkinter Not Available" message "Your Python installation does not include tkinter. Please install Python 3 from python.org (the official installer includes tkinter)." as critical'
    exit 1
fi

# Run the application
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$PYTHON" "$DIR/maximizer.py"
