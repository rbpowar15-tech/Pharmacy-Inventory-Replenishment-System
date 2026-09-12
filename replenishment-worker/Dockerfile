# ──────────────────────────────────────────────
# Replenishment Worker Container
# Logic App / Container worker that processes
# Service Bus messages and writes to Blob Storage
# ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pyodbc
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    gcc \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY worker.py .

# Run the worker
CMD ["python", "worker.py"]
