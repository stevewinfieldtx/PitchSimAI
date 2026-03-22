# MiroFish Swarm Intelligence Engine
# Clones the official MiroFish repo and runs the backend API on port 5001.
# PitchSimAI communicates with this service via REST API.
#
# MiroFish uses the same OpenRouter API key as PitchSimAI — it's passed in
# via docker-compose environment variables as LLM_API_KEY / LLM_BASE_URL.

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18 (needed for MiroFish frontend/setup)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager used by MiroFish)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Clone MiroFish
RUN git clone --depth 1 https://github.com/666ghj/MiroFish.git .

# Install backend dependencies
RUN cd backend && uv venv && uv pip install -r requirements.txt 2>/dev/null || \
    cd backend && pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    echo "Will install deps at runtime"

# Install frontend dependencies (needed for some MiroFish setup tasks)
RUN npm install --prefix . 2>/dev/null || echo "Frontend deps optional"

# Copy our startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 5001

CMD ["/app/start.sh"]
