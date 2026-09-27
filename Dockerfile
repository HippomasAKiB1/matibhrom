FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir -r requirements-cpu.txt

# Copy source code and configs
COPY src/ ./src/
COPY configs/ ./configs/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Create output directories
RUN mkdir -p outputs/{run_id}/generations outputs/{run_id}/retrieval/index outputs/cache locks

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.runner.run"]
CMD ["--config", "configs/experiments.yaml", "--split", "dev"]
