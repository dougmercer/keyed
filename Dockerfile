# Build stage
ARG IMAGE=python:3.12.9-slim-bookworm
FROM $IMAGE AS builder

# Set Python environment variables for optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the files needed for dependency installation first
COPY pyproject.toml ./

# Install dependencies first
RUN pip wheel --no-cache-dir --wheel-dir /wheels -e .

# Now copy the source code which changes more frequently
COPY src/ ./src/

# Build the package with all source code
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# Runtime stage
FROM $IMAGE

# Set Python environment variables for optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Add metadata labels
LABEL org.opencontainers.image.title="Keyed" \
      org.opencontainers.image.description="A reactive animation library for Python" \
      org.opencontainers.image.source="https://github.com/dougmercer/keyed"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home keyeduser

# Set up proper working directory with correct permissions
WORKDIR /app
RUN chown keyeduser:keyeduser /app

# Copy the built wheel from the builder stage
COPY --from=builder /wheels/*.whl /app/

# Install the wheel and clean up
RUN pip install keyed --no-index --find-links=/app && rm /app/*.whl

# Switch to non-root user
USER keyeduser

ENTRYPOINT ["keyed", "iostream"]
