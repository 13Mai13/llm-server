#!/bin/bash

# Create results directory
RESULTS_DIR="tests/performance/results/structured_vs_unstructured_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Check if API_KEY is set in environment
if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY environment variable is not set"
    exit 1
fi

# Load configuration
CONFIG_FILE="tests/performance/structured_test_cases.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found"
    exit 1
fi

# Get provider and model from config
PROVIDER=$(jq -r '.config.provider' "$CONFIG_FILE")
MODEL=$(jq -r '.config.model' "$CONFIG_FILE")

# Function to register schemas
register_schemas() {
    echo "Registering schemas..."
    local schema_ids=()
    
    # Get number of test cases
    local num_cases=$(jq '.test_cases | length' "$CONFIG_FILE")
    
    for ((i=0; i<num_cases; i++)); do
        local schema=$(jq -r --argjson idx "$i" '.test_cases[$idx].schema' "$CONFIG_FILE")
        local schema_name=$(jq -r --argjson idx "$i" '.test_cases[$idx].name' "$CONFIG_FILE")
        
        echo "Registering schema for test case: $schema_name"
        
        # Create the request body with name and json_schema fields
        local request_body=$(jq -n \
            --arg name "$schema_name" \
            --argjson json_schema "$schema" \
            '{
                "name": $name,
                "json_schema": $json_schema
            }')
        
        local response=$(curl -s -X POST "http://localhost:8000/api/v1/schemas" \
            -H "Content-Type: application/json" \
            -H "X-API-Key: $API_KEY" \
            -d "$request_body")
        
        local schema_id=$(echo "$response" | jq -r '.id')
        if [ "$schema_id" != "null" ]; then
            schema_ids+=("$schema_id")
            echo "Schema registered with ID: $schema_id"
        else
            echo "Error registering schema for $schema_name"
            echo "Response: $response"
            exit 1
        fi
    done
    
    # Save schema IDs to a file for later use
    printf '%s\n' "${schema_ids[@]}" > "$RESULTS_DIR/schema_ids.txt"
    echo "All schemas registered successfully"
}

# Function to send request and get metrics
send_request() {
    local endpoint="$1"
    local prompt="$2"
    local model="$3"
    local provider="$4"
    local schema_id="$5"
    local start_time=$(date +%s.%N)
    
    # Prepare request body
    local request_body
    if [ "$endpoint" = "structured-completions" ]; then
        request_body=$(jq -n \
            --arg prompt "$prompt" \
            --arg provider "$provider" \
            --arg model "$model" \
            --arg schema_id "$schema_id" \
            '{
                "prompt": $prompt,
                "provider": $provider,
                "model": $model,
                "max_tokens": 1000,
                "temperature": 0.7,
                "schema_id": $schema_id
            }')
    else
        request_body=$(jq -n \
            --arg prompt "$prompt" \
            --arg provider "$provider" \
            --arg model "$model" \
            '{
                "prompt": $prompt,
                "provider": $provider,
                "model": $model,
                "max_tokens": 1000,
                "temperature": 0.7
            }')
    fi
    
    # Send request and capture response
    local response=$(curl -s -X POST "http://localhost:8000/api/v1/$endpoint" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$request_body")
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    # Get metrics
    local metrics=$(curl -s -X GET "http://localhost:8000/api/v1/metrics" \
        -H "X-API-Key: $API_KEY")
    
    # Extract relevant metrics
    local input_tokens=$(echo "$metrics" | jq -r ".llm.providers.\"$provider\".input_tokens")
    local output_tokens=$(echo "$metrics" | jq -r ".llm.providers.\"$provider\".output_tokens")
    local total_requests=$(echo "$metrics" | jq -r ".llm.providers.\"$provider\".requests")
    local average_duration=$(echo "$metrics" | jq -r ".llm.models.\"$provider:$model\".timing.total.average")
    
    # Return metrics
    echo "$duration:$input_tokens:$output_tokens:$total_requests:$average_duration"
}

# Function to run test cases
run_test_cases() {
    # Read schema IDs from file
    local schema_ids=()
    while IFS= read -r line; do
        schema_ids+=("$line")
    done < "$RESULTS_DIR/schema_ids.txt"
    
    # Get number of test cases
    local num_cases=$(jq '.test_cases | length' "$CONFIG_FILE")
    
    # Initialize results file
    echo "Model,Test Case,Endpoint,Latency (s),Input Tokens,Output Tokens,Total Requests,Average Duration (s)" > "$RESULTS_DIR/results.csv"
    
    # Get list of models that support structured output
    local structured_models_response=$(curl -s -X GET "http://localhost:8000/api/v1/outlines-models" \
        -H "X-API-Key: $API_KEY")
    
    local structured_models=($(echo "$structured_models_response" | jq -r '.models[].id'))
    
    if [ ${#structured_models[@]} -eq 0 ]; then
        echo "No models found that support structured output"
        exit 1
    fi
    
    echo "Testing with models:"
    echo "Unstructured: $MODEL ($PROVIDER)"
    echo "Structured: ${structured_models[*]}"
    
    for ((i=0; i<num_cases; i++)); do
        local test_case=$(jq -r --argjson idx "$i" '.test_cases[$idx].name' "$CONFIG_FILE")
        local schema_id="${schema_ids[$i]}"
        local prompt=$(jq -r --argjson idx "$i" '.test_cases[$idx].prompt' "$CONFIG_FILE")
        
        echo "Running test case: $test_case"
        
        # Run unstructured test with configured model
        echo "Running unstructured test with $MODEL..."
        local unstructured_metrics=$(send_request "completions" "$prompt" "$MODEL" "$PROVIDER" "")
        IFS=':' read -r unstructured_duration unstructured_input_tokens unstructured_output_tokens unstructured_total_requests unstructured_average_duration <<< "$unstructured_metrics"
        
        # Run structured test with each supported model
        for structured_model in "${structured_models[@]}"; do
            echo "Running structured test with $structured_model..."
            local structured_metrics=$(send_request "structured-completions" "$prompt" "$structured_model" "$PROVIDER" "$schema_id")
            IFS=':' read -r structured_duration structured_input_tokens structured_output_tokens structured_total_requests structured_average_duration <<< "$structured_metrics"
            
            # Log results to CSV
            echo "$MODEL,$test_case,Unstructured,$unstructured_duration,$unstructured_input_tokens,$unstructured_output_tokens,$unstructured_total_requests,$unstructured_average_duration" >> "$RESULTS_DIR/results.csv"
            echo "$structured_model,$test_case,Structured,$structured_duration,$structured_input_tokens,$structured_output_tokens,$structured_total_requests,$structured_average_duration" >> "$RESULTS_DIR/results.csv"
            
            # Log to console
            echo "Unstructured ($MODEL) - Duration: $unstructured_duration seconds, Input Tokens: $unstructured_input_tokens, Output Tokens: $unstructured_output_tokens"
            echo "Structured ($structured_model) - Duration: $structured_duration seconds, Input Tokens: $structured_input_tokens, Output Tokens: $structured_output_tokens"
            echo "----------------------------------------"
        done
    done
}

# Main execution
echo "Starting structured vs unstructured performance test..."
register_schemas
run_test_cases
echo "Test completed. Results saved in $RESULTS_DIR" 