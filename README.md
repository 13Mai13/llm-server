# LLM Inference Server

A high-performance LLM inference server with structured and unstructured output validation, designed for distributed systems and optimized for large-scale LLM operations.

## Features

- High-performance LLM inference with structured output validation
- Comprehensive monitoring and metrics collection
- Efficient batch processing and connection pooling
- Robust error handling and rate limiting
- Modern API design with FastAPI

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-server.git
cd llm-server

## Local Dev
# Install dependencies
uv sync

# Run the server
uvicorn src.main:app --reload

## Docker
# Build the Docker image
docker build -t llm-server .

# Run the container
docker run -d -p 8000:8000 --env-file .env llm-server

# Verify the container is running
docker ps

```

## Configuration

Create a `.env` file with your configuration, see [example.env](/example.env) or the basics or [config.py](./src/config.py) for all the posibiities
```env
GROQ_API_KEY = [YOUR_API_KEY]
API_KEY = [YOUR_AUTH_API_KEY]
```

## API Documentation

Once the server is running, visit `/docs` for the interactive API documentation.

## Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=src
```

## Deep Dive

For a detailed technical analysis, architecture decisions, and performance considerations, see [DEEP_DIVE.md](docs/DEEP_DIVE.md). 

## Performace test

There is a section on how to run the performance test too, see [Performance_test.md](docs/performance_testing.md)

## License

MIT