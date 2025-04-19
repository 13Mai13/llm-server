# LLM Inference Server

A high-performance LLM inference server with structured and unstructured output validation.

## Features

- **Multiple LLM Provider Support**: Currently supports Groq API with plans to add more providers
- **Structured Output Validation**: Validate and transform LLM outputs using JSON schemas
- **Schema Registry**: Register and manage JSON schemas for output validation
- **Metrics and Monitoring**: Track request metrics and error rates
- **API Key Authentication**: Secure your endpoints with API key authentication
- **Health Checks**: Monitor server health and provider status

## API Endpoints

### Health Check
- `GET /api/v1/health`: Check server health and provider status

### Models
- `GET /api/v1/models`: List available models and their capabilities

### Completions
- `POST /api/v1/completions`: Generate text completions without structured validation
- `POST /api/v1/structured-completions`: Generate structured completions with schema validation

### Schema Registry
- `POST /api/v1/schemas`: Register a new JSON schema
- `GET /api/v1/schemas`: List all registered schemas
- `GET /api/v1/schemas/{schema_id}`: Get a specific schema
- `DELETE /api/v1/schemas/{schema_id}`: Delete a schema

### Metrics
- `GET /api/v1/metrics`: Get server metrics and statistics

## Structured Completions

The structured completions endpoint allows you to generate and validate LLM outputs against a JSON schema. You can either:

1. Use a registered schema by providing its ID:
```json
{
  "provider": "groq",
  "model": "llama3-8b-8192",
  "prompt": "Generate a person's information",
  "schema_id": "person_schema",
  "max_tokens": 100,
  "temperature": 0.7
}
```

2. Provide an inline schema:
```json
{
  "provider": "groq",
  "model": "llama3-8b-8192",
  "prompt": "Generate a person's information",
  "validation_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "age": {"type": "integer"}
    },
    "required": ["name", "age"]
  },
  "max_tokens": 100,
  "temperature": 0.7
}
```

3. Apply transformers to the validated output:
```json
{
  "provider": "groq",
  "model": "llama3-8b-8192",
  "prompt": "Generate a person's information",
  "validation_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "age": {"type": "integer"}
    },
    "required": ["name", "age"]
  },
  "transformers": [
    {
      "name": "lowercase_strings",
      "config": {}
    }
  ],
  "max_tokens": 100,
  "temperature": 0.7
}
```

## Authentication

All endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/health
```

## Environment Variables

- `GROQ_API_KEY`: Your Groq API key
- `API_KEY`: Your server API key for authentication
- `LOG_LEVEL`: Logging level (default: INFO)

## Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export GROQ_API_KEY=your_groq_api_key
export API_KEY=your_server_api_key
```

4. Run the server:
```bash
uvicorn src.main:app --reload
```

## Testing

Run the test suite:
```bash
pytest
```

## License

MIT 