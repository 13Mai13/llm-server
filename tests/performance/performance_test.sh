#!/bin/bash

# Create results directory if it doesn't exist
RESULTS_DIR="tests/performance/results"
mkdir -p "$RESULTS_DIR"

# Extract API key
API_KEY=$(grep "^API_KEY=" .env | cut -d '=' -f2 | tr -d '"')

# Create results file with timestamp
RESULTS_FILE="$RESULTS_DIR/performance_results_$(date +%Y%m%d_%H%M%S).txt"

# Function to run test for a scenario
run_test() {
    local name=$1
    local threads=$2
    local connections=$3
    local duration=$4
    local description=$5
    
    echo "=== Scenario: $name ===" >> "$RESULTS_FILE"
    echo "Description: $description" >> "$RESULTS_FILE"
    echo "Configuration: Threads=$threads, Connections=$connections, Duration=${duration}s" >> "$RESULTS_FILE"
    
    # Run wrk and capture output
    wrk -t$threads -c$connections -d${duration}s --latency \
        -H "X-API-Key: $API_KEY" \
        http://localhost:8000/api/v1/health >> "$RESULTS_FILE"
    
    echo -e "\n\n" >> "$RESULTS_FILE"
}

# 1. Baseline Tests
echo "=== Starting Baseline Tests ===" >> "$RESULTS_FILE"
run_test "Single Request" 1 1 30 "Testing single request performance"
run_test "Light Load" 2 5 30 "Testing under minimal load (5 concurrent users)"

# 2. Load Tests
echo "=== Starting Load Tests ===" >> "$RESULTS_FILE"
run_test "Normal Load" 2 15 60 "Testing under normal load (15 concurrent users)"
run_test "Peak Load" 2 25 60 "Testing under peak load (25 concurrent users)"

# 3. Stress Tests
echo "=== Starting Stress Tests ===" >> "$RESULTS_FILE"
run_test "Burst Load" 2 50 30 "Testing burst capacity (50 concurrent users)"
run_test "Stress Load" 2 75 30 "Testing stress conditions (75 concurrent users)"

# 4. Endurance Tests
echo "=== Starting Endurance Tests ===" >> "$RESULTS_FILE"
run_test "Sustained Load" 2 20 300 "Testing long-term stability (20 concurrent users for 5 minutes)"

# Extract key metrics from results
echo "=== Summary of Results ===" >> "$RESULTS_FILE"
echo "Test Type,Scenario,Threads,Connections,Duration,Requests/sec,Latency(avg),Latency(p95),Latency(p99)" >> "$RESULTS_FILE"

# Process each scenario's results
while IFS= read -r line; do
    if [[ $line == *"=== Scenario:"* ]]; then
        # Extract scenario name
        scenario=$(echo "$line" | sed 's/=== Scenario: //' | sed 's/ ===//')
        
        # Get test type
        test_type=$(grep -B 2 "$scenario" "$RESULTS_FILE" | grep "Starting" | sed 's/=== Starting //' | sed 's/ ===//')
        
        # Get configuration
        config_line=$(grep -A 1 "$scenario" "$RESULTS_FILE" | grep "Configuration:")
        threads=$(echo "$config_line" | grep -o "Threads=[0-9]*" | cut -d'=' -f2)
        connections=$(echo "$config_line" | grep -o "Connections=[0-9]*" | cut -d'=' -f2)
        duration=$(echo "$config_line" | grep -o "Duration=[0-9]*" | cut -d'=' -f2)
        
        # Get metrics section
        metrics_start=$(grep -n "$scenario" "$RESULTS_FILE" | cut -d: -f1)
        metrics_end=$(grep -n -m 1 "^$" "$RESULTS_FILE" | cut -d: -f1)
        metrics_section=$(sed -n "${metrics_start},${metrics_end}p" "$RESULTS_FILE")
        
        # Extract metrics
        requests=$(echo "$metrics_section" | grep "Requests/sec" | awk '{print $2}')
        latency_avg=$(echo "$metrics_section" | grep "Latency" | head -n1 | awk '{print $2}')
        latency_p95=$(echo "$metrics_section" | grep "90.000%" | awk '{print $2}')
        latency_p99=$(echo "$metrics_section" | grep "99.000%" | awk '{print $2}')
        
        # Write to summary
        echo "$test_type,$scenario,$threads,$connections,${duration}s,$requests,$latency_avg,$latency_p95,$latency_p99" >> "$RESULTS_FILE"
    fi
done < "$RESULTS_FILE"

echo "Results saved to $RESULTS_FILE"