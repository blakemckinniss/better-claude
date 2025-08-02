#!/bin/bash
# Test runner for Context Revival System with comprehensive validation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
HOOKS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$HOOKS_DIR")")"
TEST_OUTPUT_DIR="$HOOKS_DIR/test_results"

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Logging
LOG_FILE="$TEST_OUTPUT_DIR/test_context_revival_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ $1${NC}" | tee -a "$LOG_FILE"
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    local is_critical="${3:-false}"
    
    log_info "Running test: $test_name"
    
    if eval "$test_command" >> "$LOG_FILE" 2>&1; then
        log_success "$test_name"
        ((TESTS_PASSED++))
        return 0
    else
        if [ "$is_critical" = "true" ]; then
            log_error "$test_name (CRITICAL FAILURE)"
            ((TESTS_FAILED++))
            return 1
        else
            log_warning "$test_name (NON-CRITICAL FAILURE)"
            ((TESTS_FAILED++))
            return 1
        fi
    fi
}

# Pre-flight checks
preflight_checks() {
    log_info "=== Pre-flight Checks ==="
    
    # Check Python version
    run_test "Python 3.7+ available" "python3 --version | grep -E 'Python 3\.[789]|Python 3\.[1-9][0-9]'" true
    
    # Check required directories exist
    run_test "Hooks directory exists" "[ -d '$HOOKS_DIR' ]" true
    run_test "UserPromptSubmit directory exists" "[ -d '$HOOKS_DIR/hook_handlers/UserPromptSubmit' ]" true
    
    # Check core files exist
    run_test "context_revival.py exists" "[ -f '$HOOKS_DIR/hook_handlers/UserPromptSubmit/context_revival.py' ]" true
    run_test "context_manager.py exists" "[ -f '$HOOKS_DIR/hook_handlers/UserPromptSubmit/context_manager.py' ]" true
    run_test "context_revival_config.json exists" "[ -f '$HOOKS_DIR/hook_handlers/UserPromptSubmit/context_revival_config.json' ]" true
    
    # Check test files exist
    run_test "Test suite exists" "[ -f '$HOOKS_DIR/tests/test_context_revival.py' ]" true
    
    # Check Python path
    export PYTHONPATH="$HOOKS_DIR/hook_handlers/UserPromptSubmit:$PYTHONPATH"
    log_info "PYTHONPATH set to: $PYTHONPATH"
    
    log_info "Pre-flight checks completed: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo ""
}

# Syntax and import tests
syntax_tests() {
    log_info "=== Syntax and Import Tests ==="
    
    # Test Python syntax
    run_test "context_revival.py syntax check" "python3 -m py_compile '$HOOKS_DIR/hook_handlers/UserPromptSubmit/context_revival.py'"
    run_test "context_manager.py syntax check" "python3 -m py_compile '$HOOKS_DIR/hook_handlers/UserPromptSubmit/context_manager.py'"
    run_test "test_context_revival.py syntax check" "python3 -m py_compile '$HOOKS_DIR/tests/test_context_revival.py'"
    
    # Test imports (with fallback handling)
    run_test "context_revival imports" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'import context_revival; print(\"Import successful\")'"
    run_test "context_manager imports" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'import context_manager; print(\"Import successful\")'"
    
    # Test configuration loading
    run_test "Configuration loads successfully" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'import json; json.load(open(\"context_revival_config.json\"))'"
    
    log_info "Syntax tests completed: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo ""
}

# Integration tests
integration_tests() {
    log_info "=== Integration Tests ==="
    
    # Test direct CLI usage
    run_test "Context Revival CLI test" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && echo 'How to fix authentication error similar to before?' | python3 context_revival.py"
    
    # Test hook integration (simulate hook call)
    run_test "Hook integration test" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && echo '{\"prompt\": \"Debug error like last time\"}' | python3 context_revival.py"
    
    # Test configuration override
    run_test "Configuration override test" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && CLAUDE_PROJECT_DIR='$PROJECT_ROOT' python3 -c 'from context_revival import get_context_revival_hook; hook = get_context_revival_hook(); print(\"Hook initialized:\", hook.project_dir)'"
    
    log_info "Integration tests completed: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo ""
}

# Quick validation test
quick_validation() {
    log_info "=== Quick Validation ==="
    
    run_test "System initialization" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'from context_revival import get_context_revival_hook; hook = get_context_revival_hook(); print(\"✓ Hook initialized\")'"
    
    run_test "Configuration validation" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'from context_revival import get_context_revival_hook; hook = get_context_revival_hook(); print(f\"✓ Config loaded: {bool(hook.config)}\")'"
    
    run_test "Analysis functionality" "cd '$HOOKS_DIR/hook_handlers/UserPromptSubmit' && python3 -c 'from context_revival import get_context_revival_hook; hook = get_context_revival_hook(); analysis = hook.analyzer.analyze_prompt(\"Debug error similar to before\"); print(f\"✓ Analysis: confidence={analysis[\\\"confidence\\\"]:.2f}\")'"
    
    log_info "Quick validation completed: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo ""
}

# Documentation tests
documentation_tests() {
    log_info "=== Documentation Tests ==="
    
    # Check that documentation files exist and are readable
    run_test "System documentation exists" "[ -f '$HOOKS_DIR/docs/context_revival_system.md' ]"
    run_test "Performance documentation exists" "[ -f '$HOOKS_DIR/docs/context_revival_performance.md' ]"
    run_test "README exists" "[ -f '$HOOKS_DIR/docs/README_context_revival.md' ]"
    
    # Test that documentation contains expected sections
    run_test "System doc has architecture section" "grep -q '## System Architecture' '$HOOKS_DIR/docs/context_revival_system.md'"
    run_test "System doc has configuration section" "grep -q '## Configuration Guide' '$HOOKS_DIR/docs/context_revival_system.md'"
    run_test "Performance doc has benchmarks" "grep -q '## Benchmark Results' '$HOOKS_DIR/docs/context_revival_performance.md'"
    
    log_info "Documentation tests completed: $TESTS_PASSED passed, $TESTS_FAILED failed"
    echo ""
}

# Cleanup function
cleanup() {
    log_info "=== Cleanup ==="
    
    # Remove any test databases or temporary files
    find "$HOOKS_DIR" -name "test_*.db" -type f -delete 2>/dev/null || true
    find "$HOOKS_DIR" -name "*.tmp" -type f -delete 2>/dev/null || true
    
    # Clean up Python cache
    find "$HOOKS_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$HOOKS_DIR" -name "*.pyc" -type f -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main test execution
main() {
    log_info "Context Revival System Test Suite Starting"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Hooks Directory: $HOOKS_DIR"
    log_info "Log File: $LOG_FILE"
    echo ""
    
    # Initialize counters
    TESTS_PASSED=0
    TESTS_FAILED=0
    TESTS_SKIPPED=0
    
    # Run test phases
    preflight_checks
    syntax_tests
    integration_tests
    quick_validation
    documentation_tests
    
    # Cleanup
    cleanup
    
    # Final results
    echo ""
    log_info "=== Test Suite Results ==="
    log_info "Tests Passed: $TESTS_PASSED"
    log_info "Tests Failed: $TESTS_FAILED"
    log_info "Tests Skipped: $TESTS_SKIPPED"
    log_info "Total Tests: $((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "ALL TESTS PASSED"
        echo ""
        log_info "Context Revival System is ready for use!"
        log_info "Full test log available at: $LOG_FILE"
        exit 0
    else
        log_error "Some tests failed. See log for details: $LOG_FILE"
        
        # Show recent failures
        echo ""
        log_info "Recent failures:"
        grep "✗" "$LOG_FILE" | tail -5
        
        exit 1
    fi
}

# Handle script interruption
trap cleanup EXIT INT TERM

# Check if running with specific test phase
case "${1:-all}" in
    "preflight")
        preflight_checks
        ;;
    "syntax")
        syntax_tests
        ;;
    "integration")
        integration_tests
        ;;
    "validation")
        quick_validation
        ;;
    "docs")
        documentation_tests
        ;;
    "all"|*)
        main
        ;;
esac