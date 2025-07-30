#!/bin/bash
# Test runner for UserPromptSubmit hook system

set -e  # Exit on any error

echo "🧪 UserPromptSubmit Hook Test Suite"
echo "=================================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing pytest..."
    pip install pytest pytest-cov pytest-asyncio
fi

# Check if required modules are available
echo "🔍 Checking test dependencies..."
python3 -c "import psutil, aiohttp" 2>/dev/null || {
    echo "⚠️  Missing dependencies. Installing psutil and aiohttp..."
    pip install psutil aiohttp
}

cd "$(dirname "$0")"

echo
echo "📋 Available test categories:"
echo "  • unit         - Individual injection module tests (fast)"
echo "  • integration  - Module interaction tests (medium)"
echo "  • ai_contract  - AI optimization workflow tests (fast)"
echo "  • performance  - Speed and timeout tests (medium)"
echo "  • system       - End-to-end tests with real dependencies (slow)"
echo

# Default: run all except system tests
TEST_MARKER=${1:-"not system"}
VERBOSE=${2:-"-v"}

echo "🏃 Running tests with marker: $TEST_MARKER"
echo "Command: pytest hook_test.py $VERBOSE -m \"$TEST_MARKER\" --tb=short"
echo

# Run the tests
pytest hook_test.py $VERBOSE -m "$TEST_MARKER" --tb=short

# Show summary
echo
echo "✅ Test run complete!"
echo
echo "📊 Usage examples:"
echo "  ./run_tests.sh                    # Run all except system tests"
echo "  ./run_tests.sh unit               # Run only unit tests"
echo "  ./run_tests.sh integration        # Run only integration tests"
echo "  ./run_tests.sh ai_contract        # Run only AI contract tests"
echo "  ./run_tests.sh performance        # Run only performance tests" 
echo "  ./run_tests.sh system             # Run slow end-to-end tests"
echo "  ./run_tests.sh \"unit or integration\" # Run multiple categories"