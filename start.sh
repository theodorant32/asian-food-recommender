#!/bin/bash

# Download model on first startup (not during build)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>/dev/null || true

# Start the server
exec python run_server.py
