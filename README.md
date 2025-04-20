# LLM Inference Server

A high-performance LLM inference server with structured output validation, designed for distributed systems and optimized for large-scale LLM operations.

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

# Install dependencies
uv sync

# Run the server
uvicorn src.main:app --reload
```

## Configuration

Create a `.env` file with your configuration:
```env
HOST=0.0.0.0
PORT=8000
LLM_PROVIDER_API_KEY=your_api_key
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

## License

MIT

## Deep Dive

For a detailed technical analysis, architecture decisions, and performance considerations, see [DEEP_DIVE.md](docs/DEEP_DIVE.md). 

## Performace test

There is a section on how to run the performance test too, see [Performance_test.md](docs/performance_testing.md)