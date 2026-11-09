#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "======================================"
echo "       VORTEX CLI INSTALLER"
echo "======================================"

# Check Python availability
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: Python was not found."
    exit 1
fi

# Check Python version
"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 10):
    print("ERROR: Vortex requires Python 3.10 or newer.")
    raise SystemExit(1)

print(f"Python version: {sys.version.split()[0]}")
PY

# Create virtual environment if needed
if [[ ! -x ".venv/bin/python" ]]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv .venv
else
    echo "Existing virtual environment found."
fi

# Activate virtual environment
source .venv/bin/activate

# Install project and dependencies
echo "Installing Vortex and dependencies..."
python -m pip install -r requirements.txt

echo
echo "======================================"
echo "       INSTALLATION COMPLETE"
echo "======================================"

echo "Activate environment using:"
echo "source .venv/bin/activate"

echo
echo "Verify installation using:"
echo "vortex --help"

# Check Incus availability
if command -v incus >/dev/null 2>&1; then
    echo
    echo "Incus CLI: Found"
else
    echo
    echo "WARNING: Incus CLI was not found."
    echo "Install and initialize Incus before running environments."
fi