FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create necessary directories
RUN mkdir -p logs data logs/conversations

# Create default config file if it doesn't exist
# This ensures the container can start even without mounted config
RUN if [ ! -f config_marcus.json ] && [ -f config_pm_agent.json ]; then \
    cp config_pm_agent.json config_marcus.json; \
    fi

# Expose MCP stdio interface (not a network port)
# MCP uses stdio, not HTTP

# Default command - run Marcus MCP server
CMD ["python", "marcus_mcp_server.py"]