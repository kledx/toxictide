# Base Image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
# Create a dummy README.md if it doesn't exist, as it might be required by pyproject.toml
# Or just copy the project first. Let's copy requirements logic.
# Since we use pyproject.toml, we can pip install . or export requirements.
# Let's try pip install . (requires the whole source code context usually, or at least structure)

# Strategy: Copy pyproject.toml and install dependencies first for caching
# We'll generate a requirements.txt from pyproject.toml using a simple python one-liner or just use pip install
# if we copy the project structure.
# Let's upgrade pip first
RUN pip install --upgrade pip

# Copy project files
COPY . .

# Install the package in editable mode or just install dependencies
# Installing in editable mode allows running directly
RUN pip install -e .

# Expose port
EXPOSE 8001

# Command to run (using main_real.py as entrypoint)
CMD ["python", "main.py"]
