# ──────────────────────────────────────────────
# Replenishment Worker Container
# ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install curl and gnupg first, then Microsoft repo and ODBC driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    gcc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor > /usr/share/keyrings/microsoft.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] \
       https://packages.microsoft.com/debian/11/prod bullseye main" \
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
