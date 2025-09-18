#!/bin/bash

# Start the server (update this line if your entrypoint is different)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload