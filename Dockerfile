FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libcairo2 \
    libcairo2-dev \
    qtbase5-dev \
    pkg-config \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /keyed

COPY src/  ./src/
COPY setup.cfg README.md pyproject.toml ./

RUN pip install .
