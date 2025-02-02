FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libcairo2-dev \
    qtbase5-dev \
    pkg-config \
    python3-dev \
    gcc \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    libxxf86vm1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /keyed

# Copy package files
COPY src/  ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir ".[all]"
RUN pip install --no-cache-dir pyav

# Run tests
RUN pytest tests/
