# Multi-stage Dockerfile for MQTT-LLM Bridge
# Stage 1: Build stage with development dependencies
FROM python:3.11-alpine AS builder

LABEL maintainer="MQTT-LLM Bridge Team"
LABEL description="Build stage for MQTT-LLM Bridge"

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set working directory
WORKDIR /app

# Copy requirements file and project config
COPY requirements.txt pyproject.toml ./

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .

# Stage 2: Runtime stage with minimal Alpine image
FROM python:3.11-alpine AS runtime

LABEL maintainer="MQTT-LLM Bridge Team"
LABEL description="Production runtime for MQTT-LLM Bridge"
LABEL version="0.1.0"

# Install runtime dependencies only
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    tini

# Create non-root user for security
RUN addgroup -g 1000 mqttllm && \
    adduser -D -u 1000 -G mqttllm -s /bin/sh mqttllm

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

# Create directories for logs only
RUN mkdir -p /app/logs && \
    chown -R mqttllm:mqttllm /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER mqttllm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import mqtt_llm; print('Health check passed')" || exit 1

# Default environment variables (can be overridden)
ENV LOG_LEVEL=INFO \
    MQTT_BROKER=localhost \
    MQTT_PORT=1883 \
    MQTT_SUBSCRIBE_TOPIC=input/messages \
    MQTT_PUBLISH_TOPIC=output/responses \
    MQTT_QOS=0 \
    MQTT_RETAIN=false \
    MQTT_SANITIZE_RESPONSE=false \
    MQTT_TRIGGER_PATTERN=@ai \
    OLLAMA_API_URL=http://localhost:11434 \
    OLLAMA_MODEL=llama3 \
    OLLAMA_SYSTEM_PROMPT="You are a helpful assistant." \
    OLLAMA_TIMEOUT=30.0 \
    OLLAMA_MAX_TOKENS=1000

# Use tini as init system for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Default command - can be overridden
CMD ["mqtt-llm"]
