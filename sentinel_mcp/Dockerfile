FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Runtimes for multi-language fixing (JS/TS/Java)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nodejs \
        npm \
        default-jdk-headless \
        maven \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g typescript ts-node

COPY . /app/sentinel_mcp

EXPOSE 8001

CMD ["python", "-m", "sentinel_mcp.server"]
