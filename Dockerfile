ARG PLATFORM=linux/amd64
FROM --platform=${PLATFORM} python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ## Cairo
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gcc \
    ## ffmpeg
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /keyed

# Copy package files
COPY src/  ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir ".[previewer]"

ENTRYPOINT ["keyed", "iostream"]
