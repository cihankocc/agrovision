# ─── Stage 1: Frontend Build ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --prefer-offline

COPY frontend/ ./
RUN npm run build


# ─── Stage 2: Python API ──────────────────────────────────────────────────────
FROM python:3.11-slim AS api

# System dependencies (required for PyTorch on slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY api.py .
COPY src/ ./src/

# Model weights & encoders (must be present at build time)
COPY wheat_ai_unified_best.pth .
COPY fertilizer_rf_model.pkl .
COPY fert_crop_encoder.pkl .
COPY fert_soil_encoder.pkl .
COPY fert_label_encoder.pkl .
COPY fert_meta.json .

# React build output from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Runtime config
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Prod server — no --reload in production
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
