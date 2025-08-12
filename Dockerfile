FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project and install package
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# At runtime, mount your config into /app/config
# Example: -v $PWD/config:/app/config
CMD ["k8s-drift-sync", "scan", "--config", "config/config.yaml"] 