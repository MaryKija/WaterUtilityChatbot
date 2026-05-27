# ============================================================
# Water Utility Chatbot — Premium Multi-Stage Dockerfile
# ============================================================

# ------------------------------------------------------------
# Stage 1: Node.js Frontend Builder (Admin & Customer client SPAs)
# ------------------------------------------------------------
FROM node:18-alpine AS frontend-builder
WORKDIR /app

# Copy dependency files first for layer caching efficiency
COPY frontend/aqua-chat-modern-main/package*.json ./frontend/aqua-chat-modern-main/
COPY frontend/admin/package*.json ./frontend/admin/

# Build customer chat SPA
WORKDIR /app/frontend/aqua-chat-modern-main
RUN npm ci

COPY frontend/aqua-chat-modern-main/ .
RUN npm run build

# Build admin panel SPA
WORKDIR /app/frontend/admin
RUN npm ci

COPY frontend/admin/ .
RUN npm run build


# ------------------------------------------------------------
# Stage 2: Final Production Runner (Minimal python-slim image)
# ------------------------------------------------------------
FROM python:3.11-slim

# System dependencies for high-performance builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend production bundles directly from Builder stage
# (FastAPI mounts /assets and mounts admin/customer dist folders to serve SPA files)
COPY --from=frontend-builder /app/frontend/aqua-chat-modern-main/dist ./frontend/aqua-chat-modern-main/dist
COPY --from=frontend-builder /app/frontend/admin/dist ./frontend/admin/dist

# Copy Python backend application code
COPY . .

# Seed the standard SQLite database with kabwe demo data for immediate fidelity
RUN python scripts/seed_database.py || true

# Premium Security Hardening: Execute container under non-root unprivileged process
RUN useradd -u 10001 -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose FastAPI server port
EXPOSE 8000

# High-fidelity healthcheck to verify container viability
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the uvicorn production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
