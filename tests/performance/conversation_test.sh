#!/bin/bash

# Create results directory if it doesn't exist
mkdir -p tests/performance/results

# Extract API key from .env file
API_KEY=$(echo "${API_KEY}" | tr -d '"')

# Get current timestamp for results file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="tests/performance/results/conversation_results_${TIMESTAMP}.txt"

# Load configuration from prompts file
PROVIDER=$(jq -r '.config.provider' tests/performance/conversation_prompts.json)
MODEL=$(jq -r '.config.model' tests/performance/conversation_prompts.json)
MAX_TOKENS=$(jq -r '.config.max_tokens' tests/performance/conversation_prompts.json)
TEMPERATURE=$(jq -r '.config.temperature' tests/performance/conversation_prompts.json)

# Function to send a completion request
send_completion() {
    local prompt=$1
    local conversation_id=$2
    local message_number=$3
    
    # Add rate limiting - sleep for 2 seconds between requests
    sleep 2
    
    # Create the request body
    local request_body=$(cat <<EOF
{
    "prompt": "${prompt}",
    "provider": "${PROVIDER}",
    "model": "${MODEL}",
    "max_tokens": ${MAX_TOKENS},
    "temperature": ${TEMPERATURE}
}
EOF
    )
    
    curl -s -X POST "http://localhost:8000/api/v1/completions" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "${request_body}"
}

# Function to get conversation messages from JSON
get_conversation_messages() {
    local conversation_type=$1
    jq -r ".${conversation_type}[]" tests/performance/conversation_prompts.json
}

# Function to simulate a conversation
simulate_conversation() {
    local conversation_id=$1
    local conversation_type=$2
    local start_time=$(date +%s.%N)
    
    echo "=== Starting Conversation ${conversation_id} ===" >> "${RESULTS_FILE}"
    echo "Type: ${conversation_type}" >> "${RESULTS_FILE}"
    echo "Provider: ${PROVIDER}" >> "${RESULTS_FILE}"
    echo "Model: ${MODEL}" >> "${RESULTS_FILE}"
    
    # Read messages from JSON file
    while IFS= read -r message; do
        local message_start=$(date +%s.%N)
        
        echo "Sending message: ${message}" >> "${RESULTS_FILE}"
        response=$(send_completion "${message}" "${conversation_id}" "${message_number}")
        local message_end=$(date +%s.%N)
        local message_duration=$(echo "$message_end - $message_start" | bc)
        
        echo "Response time: ${message_duration}s" >> "${RESULTS_FILE}"
        echo "Response: ${response}" >> "${RESULTS_FILE}"
        echo "---" >> "${RESULTS_FILE}"
    done < <(get_conversation_messages "${conversation_type}")
    
    local end_time=$(date +%s.%N)
    local total_duration=$(echo "$end_time - $start_time" | bc)
    
    echo "Total conversation duration: ${total_duration}s" >> "${RESULTS_FILE}"
    echo "=== End Conversation ${conversation_id} ===\n" >> "${RESULTS_FILE}"
}

# Function to get metrics
get_metrics() {
    local response=$(curl -s -X GET "http://localhost:8000/api/v1/metrics" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json")
    
    # Check if response is valid JSON
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo "$response"
    else
        echo "{\"error\": \"Invalid metrics response\", \"raw\": \"$response\"}"
    fi
}

# Run test scenarios
echo "Starting conversation tests..." > "${RESULTS_FILE}"
echo "Configuration:" >> "${RESULTS_FILE}"
echo "Provider: ${PROVIDER}" >> "${RESULTS_FILE}"
echo "Model: ${MODEL}" >> "${RESULTS_FILE}"
echo "Max Tokens: ${MAX_TOKENS}" >> "${RESULTS_FILE}"
echo "Temperature: ${TEMPERATURE}" >> "${RESULTS_FILE}"
echo "---" >> "${RESULTS_FILE}"

# Run short conversations
for i in {1..3}; do
    simulate_conversation "short_$i" "short_conversation"
done

# Run medium conversations
for i in {1..2}; do
    simulate_conversation "medium_$i" "medium_conversation"
done

# Run long conversations
for i in {1..2}; do
    simulate_conversation "long_$i" "long_conversation"
done

# Get final metrics
echo "\n=== Final Metrics ===" >> "${RESULTS_FILE}"
metrics=$(get_metrics)
echo "${metrics}" >> "${RESULTS_FILE}"

# Parse and summarize metrics
echo "\n=== Metrics Summary ===" >> "${RESULTS_FILE}"

# Check if metrics contain an error
if echo "$metrics" | jq -e '.error' >/dev/null 2>&1; then
    echo "Error retrieving metrics: $(echo "$metrics" | jq -r '.error')" >> "${RESULTS_FILE}"
    echo "Raw response: $(echo "$metrics" | jq -r '.raw')" >> "${RESULTS_FILE}"
else
    # Extract LLM metrics
    llm_metrics=$(echo "$metrics" | jq -r '.llm // empty')
    if [ -n "$llm_metrics" ]; then
        echo "LLM Metrics:" >> "${RESULTS_FILE}"
        echo "Total Requests: $(echo "$llm_metrics" | jq -r '.providers."'"${PROVIDER}"'".requests // 0')" >> "${RESULTS_FILE}"
        echo "Input Tokens: $(echo "$llm_metrics" | jq -r '.providers."'"${PROVIDER}"'".input_tokens // 0')" >> "${RESULTS_FILE}"
        echo "Output Tokens: $(echo "$llm_metrics" | jq -r '.providers."'"${PROVIDER}"'".output_tokens // 0')" >> "${RESULTS_FILE}"
        echo "Average Duration: $(echo "$llm_metrics" | jq -r '.models."'"${PROVIDER}:${MODEL}"'".timing.total.average // 0')s" >> "${RESULTS_FILE}"
        echo "Error Count: $(echo "$llm_metrics" | jq -r '.models."'"${PROVIDER}:${MODEL}"'".errors | length // 0')" >> "${RESULTS_FILE}"
    else
        echo "No LLM metrics available" >> "${RESULTS_FILE}"
    fi

    # Extract request metrics
    request_metrics=$(echo "$metrics" | jq -r '.requests // empty')
    if [ -n "$request_metrics" ]; then
        echo "\nRequest Metrics:" >> "${RESULTS_FILE}"
        echo "Total Requests: $(echo "$request_metrics" | jq -r '.total // 0')" >> "${RESULTS_FILE}"
        echo "Average Duration: $(echo "$request_metrics" | jq -r '.average_duration // 0')s" >> "${RESULTS_FILE}"
    else
        echo "No request metrics available" >> "${RESULTS_FILE}"
    fi
fi

echo "\nTest results saved to ${RESULTS_FILE}" 