#!/bin/bash

# Enhanced local test runner script for Step Functions workflow
# This script sets up the local environment and runs comprehensive tests

set -e

echo "🚀 Starting Step Functions Local Test Environment..."

# Configuration
STEPFUNCTIONS_PORT=8083
SAM_API_PORT=3001
STEPFUNCTIONS_JAR="stepfunctions-local/StepFunctionsLocal.jar"
RUN_INTEGRATION_TESTS=${RUN_INTEGRATION_TESTS:-true}
RUN_UNIT_TESTS=${RUN_UNIT_TESTS:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s $url >/dev/null 2>&1; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within timeout"
    return 1
}

# Function to cleanup processes
cleanup() {
    print_status "Cleaning up processes..."
    
    # Kill Step Functions Local
    if [ -f stepfunctions.pid ]; then
        kill $(cat stepfunctions.pid) 2>/dev/null || true
        rm -f stepfunctions.pid
    fi
    
    # Kill SAM local API
    if [ -f sam-api.pid ]; then
        kill $(cat sam-api.pid) 2>/dev/null || true
        rm -f sam-api.pid
    fi
    
    # Kill any remaining processes
    pkill -f "StepFunctionsLocal.jar" 2>/dev/null || true
    pkill -f "sam local start-api" 2>/dev/null || true
    
    # Clean up temporary files
    rm -f state_machine_arn.txt
    
    print_status "Cleanup completed"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v java &> /dev/null; then
        missing_tools+=("java")
    fi
    
    if ! command -v sam &> /dev/null; then
        missing_tools+=("sam")
    fi
    
    if ! command -v python &> /dev/null; then
        missing_tools+=("python")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and try again"
        exit 1
    fi
    
    print_status "✓ All prerequisites are available"
}

# Function to setup Step Functions Local
setup_stepfunctions_local() {
    # Download Step Functions Local if not exists
    if [ ! -f "$STEPFUNCTIONS_JAR" ]; then
        print_status "Downloading Step Functions Local..."
        mkdir -p stepfunctions-local
        wget -O "$STEPFUNCTIONS_JAR" https://github.com/aws/aws-stepfunctions-local/releases/download/v1.7.0/StepFunctionsLocal.jar
        
        if [ $? -ne 0 ]; then
            print_error "Failed to download Step Functions Local"
            exit 1
        fi
    fi
    
    print_status "✓ Step Functions Local is available"
}

# Function to check port availability
check_port_availability() {
    if check_port $STEPFUNCTIONS_PORT; then
        print_warning "Port $STEPFUNCTIONS_PORT is already in use"
        print_warning "Attempting to kill existing processes..."
        pkill -f "StepFunctionsLocal.jar" 2>/dev/null || true
        sleep 2
    fi
    
    if check_port $SAM_API_PORT; then
        print_warning "Port $SAM_API_PORT is already in use"
        print_warning "Attempting to kill existing processes..."
        pkill -f "sam local start-api" 2>/dev/null || true
        sleep 2
    fi
}

# Function to start services
start_services() {
    # Build SAM application
    print_status "Building SAM application..."
    sam build
    
    if [ $? -ne 0 ]; then
        print_error "SAM build failed"
        exit 1
    fi
    
    # Start SAM local API
    print_status "Starting SAM local API on port $SAM_API_PORT..."
    sam local start-api --port $SAM_API_PORT &
    echo $! > sam-api.pid
    
    # Start Step Functions Local
    print_status "Starting Step Functions Local on port $STEPFUNCTIONS_PORT..."
    cd stepfunctions-local
    java -jar StepFunctionsLocal.jar --lambda-endpoint http://localhost:$SAM_API_PORT &
    echo $! > ../stepfunctions.pid
    cd ..
    
    # Wait for services to be ready
    wait_for_service "http://localhost:$SAM_API_PORT/" "SAM Local API"
    wait_for_service "http://localhost:$STEPFUNCTIONS_PORT/" "Step Functions Local"
}

# Function to create state machine
create_state_machine() {
    print_status "Creating Step Functions state machine..."
    
    # Set environment variables for the script
    export STEPFUNCTIONS_ENDPOINT=http://localhost:$STEPFUNCTIONS_PORT
    
    # Use the dedicated script
    python scripts/create_state_machine.py
    
    if [ $? -ne 0 ]; then
        print_error "Failed to create state machine"
        exit 1
    fi
    
    # Set environment variable for tests
    export STATE_MACHINE_ARN=$(cat state_machine_arn.txt)
    print_status "State machine ARN: $STATE_MACHINE_ARN"
}

# Function to run tests
run_tests() {
    local test_exit_code=0
    
    print_status "🧪 Running test suite..."
    
    # Set environment variables
    export STEPFUNCTIONS_ENDPOINT=http://localhost:$STEPFUNCTIONS_PORT
    export STATE_MACHINE_ARN=$(cat state_machine_arn.txt)
    
    # Run integration tests
    if [ "$RUN_INTEGRATION_TESTS" = "true" ]; then
        print_status "Running integration tests..."
        python tests/integration_test.py --config tests/test_config.json --output integration_test_report.json --verbose
        
        if [ $? -ne 0 ]; then
            print_error "Integration tests failed"
            test_exit_code=1
        else
            print_status "✓ Integration tests passed"
        fi
    fi
    
    # Run unit tests with pytest
    if [ "$RUN_UNIT_TESTS" = "true" ]; then
        print_status "Running unit tests with pytest..."
        python -m pytest tests/ -v --tb=short --junit-xml=test-results.xml
        
        if [ $? -ne 0 ]; then
            print_error "Unit tests failed"
            test_exit_code=1
        else
            print_status "✓ Unit tests passed"
        fi
    fi
    
    # Generate comprehensive report
    print_status "Generating comprehensive test report..."
    python scripts/generate_test_report.py
    
    return $test_exit_code
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --integration-only    Run only integration tests"
    echo "  --unit-only          Run only unit tests"
    echo "  --help               Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  RUN_INTEGRATION_TESTS  Set to 'false' to skip integration tests (default: true)"
    echo "  RUN_UNIT_TESTS        Set to 'false' to skip unit tests (default: true)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --integration-only)
            RUN_INTEGRATION_TESTS=true
            RUN_UNIT_TESTS=false
            shift
            ;;
        --unit-only)
            RUN_INTEGRATION_TESTS=false
            RUN_UNIT_TESTS=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Step Functions Local Test Runner"
    print_status "Integration Tests: $RUN_INTEGRATION_TESTS"
    print_status "Unit Tests: $RUN_UNIT_TESTS"
    
    check_prerequisites
    setup_stepfunctions_local
    check_port_availability
    start_services
    create_state_machine
    
    if run_tests; then
        print_status "🎉 All tests completed successfully!"
        exit 0
    else
        print_error "💥 Some tests failed!"
        exit 1
    fi
}

# Run main function
main