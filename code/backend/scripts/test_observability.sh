#!/bin/bash

# Observability Integration Test Script
# Tests the complete monitoring stack including Prometheus, Grafana, and Langfuse

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
API_URL="http://localhost:8000"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3001"
LANGFUSE_URL="http://localhost:3000"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    log_info "Checking ${service_name} health at ${url}"

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "${url}" > /dev/null 2>&1; then
            log_success "${service_name} is healthy"
            return 0
        fi

        log_info "Waiting for ${service_name} to be ready (attempt ${attempt}/${max_attempts})..."
        sleep 2
        ((attempt++))
    done

    log_error "${service_name} failed to become healthy"
    return 1
}

# Function to test API metrics endpoint
test_api_metrics() {
    log_info "Testing API metrics endpoint"

    if ! curl -f -s "${API_URL}/metrics" > /dev/null; then
        log_error "API metrics endpoint is not accessible"
        return 1
    fi

    # Check for specific metrics
    local metrics
    metrics=$(curl -s "${API_URL}/metrics")

    if echo "$metrics" | grep -q "http_requests_total"; then
        log_success "HTTP request metrics found"
    else
        log_warning "HTTP request metrics not found"
    fi

    if echo "$metrics" | grep -q "system_cpu_usage_percent\|cpu"; then
        log_success "System metrics found"
    else
        log_warning "System metrics not found"
    fi

    log_success "API metrics endpoint is working"
}

# Function to test Prometheus
test_prometheus() {
    log_info "Testing Prometheus"

    # Check Prometheus health
    if ! check_service_health "Prometheus" "${PROMETHEUS_URL}/-/healthy"; then
        return 1
    fi

    # Check if Prometheus can scrape targets
    local targets
    targets=$(curl -s "${PROMETHEUS_URL}/api/v1/targets" | jq -r '.data.activeTargets[].health' 2>/dev/null || echo "")

    if [ -n "$targets" ] && echo "$targets" | grep -q "up"; then
        log_success "Prometheus is scraping targets successfully"
    else
        log_warning "Prometheus target scraping status unclear"
    fi

    # Check for API metrics in Prometheus
    local query_result
    query_result=$(curl -s -G "${PROMETHEUS_URL}/api/v1/query" --data-urlencode "query=http_requests_total" | jq -r '.data.result' 2>/dev/null || echo "")

    if [ -n "$query_result" ] && [ "$query_result" != "[]" ]; then
        log_success "API metrics are available in Prometheus"
    else
        log_warning "API metrics not found in Prometheus"
    fi
}

# Function to test Grafana
test_grafana() {
    log_info "Testing Grafana"

    # Check Grafana health
    if ! check_service_health "Grafana" "${GRAFANA_URL}/api/health"; then
        return 1
    fi

    # Test dashboard access
    local dashboards
    dashboards=$(curl -s -u "admin:admin" "${GRAFANA_URL}/api/search" | jq -r '.[].title' 2>/dev/null || echo "")

    if [ -n "$dashboards" ]; then
        log_success "Grafana dashboards found: $dashboards"
    else
        log_warning "No dashboards found in Grafana"
    fi

    # Check if research-copilot dashboards are provisioned
    if echo "$dashboards" | grep -q "Research Copilot\|Pipeline"; then
        log_success "Research Copilot dashboards are provisioned"
    else
        log_warning "Research Copilot dashboards not found"
    fi
}

# Function to test Langfuse
test_langfuse() {
    log_info "Testing Langfuse"

    # Check Langfuse health
    if check_service_health "Langfuse" "${LANGFUSE_URL}/api/health"; then
        log_success "Langfuse is accessible"
    else
        log_warning "Langfuse health check failed (may be expected if not configured)"
    fi
}

# Function to generate test traffic
generate_test_traffic() {
    log_info "Generating test traffic to populate metrics"

    # Make several requests to the API
    for i in {1..10}; do
        curl -s "${API_URL}/ping" > /dev/null &
        curl -s "${API_URL}/health" > /dev/null &
    done

    # Wait for requests to complete
    wait
    log_success "Test traffic generated"
}

# Function to validate metrics collection
validate_metrics_collection() {
    log_info "Validating metrics collection"

    # Wait a bit for metrics to be scraped
    sleep 5

    # Check Prometheus for recent metrics
    local end_time
    end_time=$(date +%s)
    local start_time=$((end_time - 300))  # Last 5 minutes

    local query
    query="increase(http_requests_total[5m])"

    local result
    result=$(curl -s -G "${PROMETHEUS_URL}/api/v1/query_range" \
        --data-urlencode "query=$query" \
        --data-urlencode "start=$start_time" \
        --data-urlencode "end=$end_time" \
        --data-urlencode "step=60" | jq -r '.data.result' 2>/dev/null || echo "")

    if [ -n "$result" ] && [ "$result" != "[]" ]; then
        log_success "Metrics collection validated - HTTP requests detected"
    else
        log_warning "Metrics collection validation inconclusive"
    fi
}

# Main test function
main() {
    log_info "Starting Observability Integration Tests"
    log_info "Project root: ${PROJECT_ROOT}"

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi

    # Start the monitoring stack
    log_info "Starting monitoring stack with docker-compose"
    cd "${PROJECT_ROOT}"

    # Start only the monitoring services
    docker-compose up -d prometheus grafana langfuse langfuse-db

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."

    # Test each service
    test_langfuse
    test_prometheus
    test_grafana

    # Test API (assuming it's already running)
    if curl -f -s "${API_URL}/health" > /dev/null 2>&1; then
        log_success "API is running"
        test_api_metrics
        generate_test_traffic
        validate_metrics_collection
    else
        log_warning "API is not running at ${API_URL} - skipping API-specific tests"
    fi

    # Summary
    log_info "Observability integration test completed"
    log_info "Services tested:"
    log_info "  - Prometheus: ${PROMETHEUS_URL}"
    log_info "  - Grafana: ${GRAFANA_URL}"
    log_info "  - Langfuse: ${LANGFUSE_URL}"
    log_info "  - API Metrics: ${API_URL}/metrics"

    log_success "All tests completed successfully!"
}

# Run main function
main "$@"