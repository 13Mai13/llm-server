# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv ~/.local/bin/uv /usr/local/bin/uv

# Copy project files
COPY . .

# Install Python dependencies
RUN uv sync

# Expose the port the app runs on
EXPOSE 8000

# Create a startup script
RUN echo '#!/bin/sh\n\
echo "Checking environment variables..."\n\
if [ -z "$API_KEY" ]; then\n\
    echo "Error: API_KEY is not set"\n\
    exit 1\n\
else\n\
    echo "API_KEY is set"\n\
fi\n\
exec /app/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"] 