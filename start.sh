#!/bin/bash
# start.sh - Railway startup script

# Set Google credentials if provided
if [ ! -z "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "$GOOGLE_CREDENTIALS_JSON" > key.json
    export GOOGLE_APPLICATION_CREDENTIALS="key.json"
    echo "✅ Google Cloud credentials set"
fi

# Start the application
uvicorn main:app --host 0.0.0.0 --port $PORT