#!/bin/bash

# Usage: ./count_all_tokens.sh [--mode openai|llama]
# Defaults: mode=openai

MODE="openai"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --mode) MODE="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

source tokenenv/bin/activate

# Base path relative to the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_ROOT="$SCRIPT_DIR/../data/prompts"

find "$PROMPT_ROOT" -type f -name '*.txt' | while read -r file; do
    echo "⟐ ${file#$PROMPT_ROOT/}"
    MODE=$MODE python "$SCRIPT_DIR/count_tokens.py" "$file"
done
