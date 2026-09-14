FROM python:3.11-slim

WORKDIR /app/safepass-ai

# System build dependencies for geospatial / ML packages (hdbscan, shapely, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY safepass-ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY safepass-ai/ .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
