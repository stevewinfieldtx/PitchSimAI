#!/bin/bash
set -e

cd /app

# Write environment variables to .env for MiroFish to pick up
cat > .env <<EOF
LLM_API_KEY=${LLM_API_KEY:-}
LLM_BASE_URL=${LLM_BASE_URL:-https://openrouter.ai/api/v1}
LLM_MODEL_NAME=${LLM_MODEL_NAME:-openai/gpt-4o-mini}
ZEP_API_KEY=${ZEP_API_KEY:-}
BOOST_LLM_API_KEY=${BOOST_LLM_API_KEY:-}
BOOST_LLM_BASE_URL=${BOOST_LLM_BASE_URL:-https://openrouter.ai/api/v1}
BOOST_LLM_MODEL_NAME=${BOOST_LLM_MODEL_NAME:-openai/gpt-4o-mini}
EOF

echo "=== MiroFish Configuration ==="
echo "LLM_BASE_URL: ${LLM_BASE_URL}"
echo "LLM_MODEL_NAME: ${LLM_MODEL_NAME}"
echo "ZEP_API_KEY: $([ -n "${ZEP_API_KEY}" ] && echo 'SET' || echo 'NOT SET')"
echo "=============================="

# Install backend deps if needed
cd /app/backend
pip install -r requirements.txt 2>/dev/null || echo "Dependencies already installed"

# MiroFish entry point is backend/run.py
echo "Starting MiroFish backend on port 5001..."
python run.py
