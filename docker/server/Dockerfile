# Build context: repository root
FROM python:3.11-slim

WORKDIR /app

# Install backend deps + PostgreSQL driver (no change to backend/requirements.txt)
COPY backend/requirements.txt requirements-base.txt
COPY docker/server/requirements-docker.txt requirements-docker.txt
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy backend and frontend (backend serves frontend from base_path/frontend/dist)
COPY backend /app/backend
COPY frontend/dist /app/frontend/dist

WORKDIR /app/backend

EXPOSE 8443

# Use run_https.py so the server runs with SSL (HTTPS); certs are generated at first start
CMD ["python", "run_https.py"]
