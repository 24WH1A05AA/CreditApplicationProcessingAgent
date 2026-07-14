#!/bin/bash
set -e

echo "Starting Credit Processing Streamlit Frontend..."

# Start Streamlit UI application
exec streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
