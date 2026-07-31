#!/bin/bash
cd "$(dirname "$0")"

# Ensure uv is available
if ! command -v uv &> /dev/null; then
    echo "ERROR: 'uv' not found. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    read -p "Press Enter to close..."
    exit 1
fi

echo "========================================"
echo "  Contract Downloader — Starting GUI"
echo "========================================"

uv run contract-downloader

# Keep terminal open briefly so user can see any errors
if [ $? -ne 0 ]; then
    echo ""
    echo "Application exited with errors (code $?)."
    read -p "Press Enter to close..."
fi
