# ──────────────────────────────────────────────
# Stage 1: Base image
# ──────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# ──────────────────────────────────────────────
# Install system dependencies for pyodbc
# (ODBC Driver 18 for Azure SQL)
# ──────────────────────────────────────────────
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

# ──────────────────────────────────────────────
# Install Python dependencies
# ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────
# Copy application code and static frontend
# ──────────────────────────────────────────────
COPY app/ ./app/
COPY static/ ./static/

# ──────────────────────────────────────────────
# Expose port 8000 for the FastAPI application
# Application Gateway will route traffic to this port
# ──────────────────────────────────────────────
EXPOSE 8000

# ──────────────────────────────────────────────
# Start the FastAPI application
# ──────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
