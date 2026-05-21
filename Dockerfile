# ============================================================
# Water Utility Chatbot — Backend Dockerfile
# ============================================================
# Builds a self-contained image that:
#   1. Installs Python dependencies
#   2. Seeds the SQLite database with demo data
#   3. Starts the FastAPI server on port 8000
#
# Usage:
#   docker build -t water-chatbot .
#   docker run -p 8000:8000 --env-file .env water-chatbot
# ============================================================

FROM python:3.11-slim

# System dependencies (needed by sentence-transformers / faiss)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Seed the database with demo data so the dashboard is populated on first run
RUN python scripts/seed_database.py || true

# Expose the FastAPI port
EXPOSE 8000

# Health check — verifies the server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
