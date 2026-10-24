FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure storage and test pack dirs exist
RUN mkdir -p storage_data test_pack/outputs test_pack/logs certification_pack

EXPOSE 8000 8080

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
