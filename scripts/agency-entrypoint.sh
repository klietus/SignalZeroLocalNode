#!/bin/bash

echo "Starting SignalZero API + Agency Loop"

# Start API server in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Run agency loop in foreground
python3 app/agency_loop.py
