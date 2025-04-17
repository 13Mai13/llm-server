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
