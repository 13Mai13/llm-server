# Performance Testing Guide

This document outlines how to run performance tests against the LLM inference server and collect various metrics.

## Prerequisites

1. Install required tools:
```bash
# Install wrk for HTTP benchmarking
brew install wrk

# Install jq for JSON processing
brew install jq
```

## Running Performance Tests

### 1. Build and Run Docker Container

```bash
# Build the Docker image
docker build -t llm-server .

# Run the container
docker run -d -p 8000:8000 --env-file .env llm-server

# Verify the container is running
docker ps
```

### 2. Run Performance Tests

```bash
# Extract API key from .env file
API_KEY=$(grep "^API_KEY=" .env | cut -d '=' -f2 | tr -d '"')

# Run test with detailed latency metrics
wrk -t4 -c10 -d30s --latency -H "X-API-Key: ${API_KEY}" http://localhost:8000/api/v1/health
```

## Running All Scenarios

Make the script executable and run it:
```bash
chmod +x tests/performance/performance_test.sh
./tests/performance/performance_test.sh
```

The script will:
1. Create a timestamped results file
2. Run all scenarios sequentially
3. Save raw results for each scenario
4. Extract and format key metrics into a CSV-like summary
5. Save everything to a single file

To view specific metrics from the results file:
```bash
# View all results
cat "$RESULTS_FILE"

# View just the summary
grep -A 1 "Summary of Results" "$RESULTS_FILE"

# View specific scenario
grep -A 10 "Scenario: Light Load" "$RESULTS_FILE"
```

## Cleanup

After testing, you can stop and remove the container:
```bash
# Stop the container
docker stop $(docker ps -q --filter ancestor=llm-server)

# Remove the container
docker rm $(docker ps -a -q --filter ancestor=llm-server)
```

## Interpreting Results

- **Throughput**: Number of requests processed per second
  - Higher is better
  - Should be stable under load
  - Measured in Requests/sec

- **Latency**: Time taken to process a request
  - Average: Overall response time
  - p95: 95th percentile (95% of requests are faster)
  - p99: 99th percentile (99% of requests are faster)

## Best Practices

1. Run tests for at least 30 seconds to get stable metrics
2. Start with lower concurrency and gradually increase
3. Run multiple tests to ensure consistency
4. Document baseline metrics for future comparison

## Test Scenarios

### 1. Health Check Endpoint
**Purpose**: Tests basic server responsiveness and connection handling
```bash
# Run health check test
wrk -t4 -c10 -d30s --latency -H "X-API-Key: ${API_KEY}" http://localhost:8000/api/v1/health
```
**Metrics**:
- Response time for basic endpoint
- Server availability
- Connection handling

### 2. Model List Endpoint
**Purpose**: Tests model information retrieval performance
```bash
# Run model list test
wrk -t4 -c10 -d30s --latency -H "X-API-Key: ${API_KEY}" http://localhost:8000/api/v1/models
```
**Metrics**:
- Model list retrieval speed
- JSON parsing performance
- Cache effectiveness

### 3. Structured Output Tests
**Purpose**: Tests structured JSON generation performance across different models

**Important Note**: Each call to the structured endpoint requires a new schema to be generated. The schema cannot be cached or reused between calls, as it must match the exact structure of the expected output. This ensures type safety and validation for each request.

#### Simple JSON Object
```bash
# Test with GPT-3.5
curl -X POST http://localhost:8000/api/v1/structured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "prompt": "Generate a simple user object with name, age, and email",
    "schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "email": {"type": "string"}
      }
    }
  }'
```
**Metrics**:
- Basic structured output generation
- Schema validation performance
- Small payload handling
- Schema generation overhead

#### Nested JSON Object
```bash
# Test with Claude-2
curl -X POST http://localhost:8000/api/v1/structured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-2",
    "prompt": "Generate a complex user profile with nested objects",
    "schema": {
      "type": "object",
      "properties": {
        "user": {
          "type": "object",
          "properties": {
            "personal": {
              "type": "object",
              "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
              }
            },
            "contact": {
              "type": "object",
              "properties": {
                "email": {"type": "string"},
                "phone": {"type": "string"}
              }
            }
          }
        }
      }
    }
  }'
```
**Metrics**:
- Complex structured output generation
- Nested schema validation
- Medium payload handling

#### Array of Objects
```bash
# Test with GPT-4
curl -X POST http://localhost:8000/api/v1/structured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "prompt": "Generate a list of 5 user objects",
    "schema": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer"},
          "email": {"type": "string"},
          "address": {
            "type": "object",
            "properties": {
              "street": {"type": "string"},
              "city": {"type": "string"},
              "zip": {"type": "string"}
            }
          }
        }
      }
    }
  }'
```
**Metrics**:
- Array generation performance
- Multiple object validation
- Large payload handling

### 4. Unstructured Output Tests
**Purpose**: Tests raw text generation performance

```bash
# Test with Groq llama3
curl -X POST http://localhost:8000/api/v1/unstructured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3-8b-8192",
    "prompt": "Write a detailed product description for a smartphone",
    "max_tokens": 500
  }'
```
**Metrics**:
- Raw text generation speed
- Token generation rate
- Long-form content handling

### 5. Batch Processing Tests
**Purpose**: Tests concurrent request handling and batch processing efficiency

```bash
# Run batch processing test
wrk -t8 -c50 -d60s --latency \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -s tests/performance/batch_test.lua \
  http://localhost:8000/api/v1/unstructured
```
**Metrics**:
- Concurrent request handling
- Batch processing efficiency
- Resource utilization under load

### 6. Conversation Testing
**Purpose**: Tests multi-turn conversation handling and context management

```bash
# Test conversation with GPT-4
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Tell me about the solar system."},
      {"role": "assistant", "content": "The solar system consists of the Sun and everything that orbits around it..."},
      {"role": "user", "content": "What about the planets?"}
    ],
    "max_tokens": 500
  }'
```
**Metrics**:
- Context window management
- Message history handling
- Token usage per turn
- Response consistency
- Memory usage with growing context

### 7. Structured vs Unstructured Comparison
**Purpose**: Compares performance between structured and unstructured endpoints for the same task

```bash
# Test both endpoints with the same prompt
# Structured endpoint
curl -X POST http://localhost:8000/api/v1/structured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "prompt": "Generate a user profile with name, age, email, and address",
    "schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "email": {"type": "string"},
        "address": {
          "type": "object",
          "properties": {
            "street": {"type": "string"},
            "city": {"type": "string"},
            "zip": {"type": "string"}
          }
        }
      }
    }
  }'

# Unstructured endpoint
curl -X POST http://localhost:8000/api/v1/unstructured \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "prompt": "Generate a user profile with name, age, email, and address in JSON format",
    "max_tokens": 500
  }'
```
**Metrics**:
- Response time comparison
- Token usage comparison
- Error rate comparison
- Schema validation overhead
- Output quality comparison
- Resource utilization differences

**Test Cases**:
1. **Simple Object Generation**:
   - Input tokens: ~23
   - Output tokens: ~46
   - Tests basic structured vs unstructured performance

2. **Nested Object Generation**:
   - Input tokens: ~48
   - Output tokens: ~396
   - Tests complex structured output handling

3. **Array of Objects**:
   - Input tokens: ~68
   - Output tokens: ~760
   - Tests large structured output handling

**Analysis Focus**:
1. **Latency Comparison**:
   - Structured endpoint overhead
   - Schema validation impact
   - Token generation differences

2. **Resource Usage**:
   - CPU utilization patterns
   - Memory usage differences
   - Network bandwidth requirements

3. **Quality Metrics**:
   - Output format accuracy
   - Schema compliance rate
   - Error handling effectiveness

## Test Results Analysis

Each test scenario generates the following metrics:

1. **Latency Metrics**:
   - Average response time
   - 95th percentile latency
   - 99th percentile latency
   - Maximum response time

2. **Throughput Metrics**:
   - Requests per second
   - Successful requests
   - Failed requests
   - Error rate

3. **Resource Metrics**:
   - CPU utilization
   - Memory usage
   - Network I/O
   - Connection pool usage

4. **Model-Specific Metrics**:
   - Token generation rate
   - Input/output token ratio
   - Model initialization time
   - Cache hit rate

## Running All Tests

To run all tests sequentially with proper metrics collection:

```bash
# Make the script executable
chmod +x tests/performance/performance_test.sh

# Run all tests
./tests/performance/performance_test.sh
```

The script will:
1. Create a timestamped results directory
2. Run each test scenario
3. Collect and format metrics
4. Generate a comprehensive report
5. Save raw data for further analysis

## Best Practices

1. **Test Environment**:
   - Use consistent hardware/VM specifications
   - Ensure network stability
   - Monitor system resources
   - Document environment details

2. **Test Execution**:
   - Run each test multiple times
   - Allow for warm-up periods
   - Monitor for anomalies
   - Document any issues

3. **Results Analysis**:
   - Compare against baselines
   - Look for patterns
   - Identify bottlenecks
   - Document findings

4. **Reporting**:
   - Include environment details
   - Document test parameters
   - Present key metrics
   - Provide recommendations

## Running Specific Test Scripts

### Conversation Testing Script
The `conversation_test.sh` script tests multi-turn conversation handling with different conversation lengths.

**Prerequisites**:
1. Ensure `conversation_prompts.json` is properly configured with:
   - Provider and model settings
   - Conversation types (short, medium, long)
   - Test prompts

**Usage**:
```bash
# Make the script executable
chmod +x tests/performance/conversation_test.sh

# Set API key
export API_KEY="your-api-key"

# Run the test
./tests/performance/conversation_test.sh
```

**What the script does**:
1. Creates a timestamped results file
2. Runs three types of conversations:
   - Short conversations (3 iterations)
   - Medium conversations (2 iterations)
   - Long conversations (2 iterations)
3. Collects metrics for each conversation:
   - Response times
   - Token usage
   - Error rates
4. Generates a final metrics summary

**Output**:
- Results saved to: `tests/performance/results/conversation_results_TIMESTAMP.txt`
- Includes:
  - Individual conversation metrics
  - Total conversation durations
  - Final system metrics
  - Error counts and types

### Structured vs Unstructured Testing Script
The `structured_vs_unstructured_test.sh` script compares performance between structured and unstructured endpoints.

**Prerequisites**:
1. Ensure `structured_test_cases.json` is properly configured with:
   - Test cases and their schemas
   - Provider and model settings
   - Test prompts

**Usage**:
```bash
# Make the script executable
chmod +x tests/performance/structured_vs_unstructured_test.sh

# Set API key
export API_KEY="your-api-key"

# Run the test
./tests/performance/structured_vs_unstructured_test.sh
```

**What the script does**:
1. Creates a timestamped results directory
2. Registers schemas for structured testing
3. Runs test cases for both endpoints:
   - Simple JSON Object
   - Nested JSON Object
   - Array of Objects
4. Collects metrics for each test:
   - Latency
   - Input/Output tokens
   - Request counts
   - Average durations

**Output**:
- Results saved to: `tests/performance/results/structured_vs_unstructured_TIMESTAMP/`
- Includes:
  - `results.csv` with detailed metrics
  - Schema registration logs
  - Console output with real-time results

**Interpreting Results**:
1. **CSV Format**:
   ```
   Model,Test Case,Endpoint,Latency (s),Input Tokens,Output Tokens,Total Requests,Average Duration (s)
   ```
2. **Key Comparisons**:
   - Latency differences between endpoints
   - Token usage patterns
   - Error rates
   - Resource utilization

**Best Practices for Running Tests**:
1. Run tests in isolation
2. Monitor system resources
3. Allow for warm-up periods
4. Run multiple iterations
5. Document environment conditions
