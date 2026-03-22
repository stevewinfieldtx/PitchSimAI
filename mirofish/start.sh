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

# Ensure backend dependencies are installed
cd /app/backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Using virtual environment"
else
    echo "No venv found, using system Python"
fi

# Try to install deps if not already done
pip install -r requirements.txt 2>/dev/null || echo "Dependencies already installed"

# Start MiroFish backend API on port 5001
echo "Starting MiroFish backend on port 5001..."
python -m flask run --host 0.0.0.0 --port 5001 2>/dev/null || \
    python app.py 2>/dev/null || \
    python main.py 2>/dev/null || \
    echo "ERROR: Could not start MiroFish backend. Check the entry point."
