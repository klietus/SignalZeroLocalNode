#!/bin/bash

# Send query to symbolic reasoning server
# Usage: ./query_session.sh "Your query here" session-id

QUERY="$2"
SESSION="$1"

if [ -z "$QUERY" ] || [ -z "$SESSION" ]; then
  echo "Usage: ./query_session.sh \"Your query here\" session-id"
  exit 1
fi

# URL for local FastAPI server (adjust port if needed)
API_URL="http://localhost:8000/query"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{ "query": "'"$QUERY"'", "session_id": "'"$SESSION"'" }'
