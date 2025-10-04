FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install OPA
RUN curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64 && \
    chmod +x /usr/local/bin/opa

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
