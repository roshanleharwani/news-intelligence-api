#!/bin/bash

# 1. Boot the internal API (and the ingestion worker) in the background on port 8000
# We bind it to 127.0.0.1 so it stays strictly internal and secure.
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# 2. Give the API 3 seconds to fully boot up and initialize the database
sleep 3

# 3. Boot the Streamlit UI in the foreground to keep the container alive.
# We bind this to 0.0.0.0 so the outside world (Railway) can route traffic to it.
streamlit run frontend/ui.py --server.port ${PORT:-8501} --server.address 0.0.0.0