# UserPromptSubmit Hook Test Suite Documentation

## Overview

This comprehensive test suite verifies all injection modules consumed by `UserPromptSubmit.py` are working properly. The test suite follows industry best practices with extensive mocking, categorized tests, and performance validation.

## Files Created

- **`hook_test.py`** - Main test suite with 25+ comprehensive tests
- **`run_tests.sh`** - Convenient test runner script with category filtering
- **`pyproject.toml`** - pytest configuration for test markers and settings
- **`TEST_DOCUMENTATION.md`** - This documentation file

## Test Categories

### 🔧 Unit Tests (`@pytest.mark.unit`)
Tests individual injection modules with fully mocked dependencies:

- **Git injection**: Tests clean repo, modified files, non-git directories
- **Runtime monitoring**: Tests system metrics with mocked psutil
- **Test status**: Tests pytest/jest result parsing
- **LSP diagnostics**: Tests error/warning parsing from language servers
- **Context history**: Tests recent file/command history tracking
- **All other injections**: prefix, suffix, zen, content, trigger, tree-sitter, MCP, agent

### ⚙️ Integration Tests (`@pytest.mark.integration`)
Tests module interaction and context assembly:

- **Context assembly without AI**: Verifies raw context concatenation
- **Context assembly with AI**: Tests AI optimization workflow
- **Input handling**: Tests empty prompts, malformed data
- **Environment variables**: Tests missing/invalid configurations

### 🤖 AI Contract Tests (`@pytest.mark.ai_contract`)
Tests AI optimization workflow with mocked OpenRouter API:

- **Successful optimization**: Mocks API success responses
- **API failures**: Tests fallback to rule-based optimization
- **Missing API key**: Tests graceful degradation
- **Timeout handling**: Verifies 3-second timeout enforcement

### 🚀 Performance Tests (`@pytest.mark.performance`)
Ensures hooks don't slow down prompts:

- **Context assembly speed**: Must complete within 1 second
- **AI timeout enforcement**: Verifies proper timeout handling
- **Resource usage**: Monitors memory and CPU during execution

### 🔧 System Tests (`@pytest.mark.system`)
End-to-end tests with minimal mocking (run sparingly):

- **Real git repository**: Tests with actual git commands
- **Full integration**: Tests complete workflow with real dependencies

### 🛡️ Error Handling Tests
Tests graceful degradation and fault tolerance:

- **Exception handling**: Tests injection module failures
- **Missing dependencies**: Tests behavior with missing environment variables
- **Malformed inputs**: Tests resilience to invalid data

## Usage Instructions

### Quick Start
```bash
# Run all tests except slow system tests (recommended)
./run_tests.sh

# Run specific test categories
./run_tests.sh unit              # Fast unit tests only
./run_tests.sh integration       # Integration tests only
./run_tests.sh ai_contract       # AI optimization tests only
./run_tests.sh performance       # Performance validation tests
./run_tests.sh system            # Slow end-to-end tests
```

### Advanced Usage
```bash
# Run multiple categories
./run_tests.sh "unit or integration"

# Run with different verbosity
./run_tests.sh unit -q           # Quiet output
./run_tests.sh unit -v           # Verbose output (default)
./run_tests.sh unit -vv          # Very verbose output

# Direct pytest usage
pytest hook_test.py -v -m unit   # Unit tests only
pytest hook_test.py -x           # Stop on first failure
pytest hook_test.py --tb=short   # Shorter traceback format
pytest hook_test.py --lf         # Run last failed tests only
```

### CI/CD Integration
```bash
# For continuous integration (includes performance tests)
pytest hook_test.py -v -m "not system" --tb=short

# For nightly builds (includes all tests)
pytest hook_test.py -v --tb=short
```

## Test Dependencies

The test suite automatically checks for and installs required dependencies:

- **pytest** - Test framework
- **pytest-cov** - Coverage reporting (optional)
- **pytest-asyncio** - Async test support
- **psutil** - System monitoring (for runtime injection tests)
- **aiohttp** - HTTP client (for AI optimization tests)

## Mocking Strategy

### External Dependencies Mocked:
- **subprocess.run** - For git commands and system calls
- **psutil** - For system resource monitoring
- **aiohttp.ClientSession** - For OpenRouter API calls
- **File system operations** - For reading config/history files
- **Environment variables** - For configuration testing

### Benefits of Extensive Mocking:
- **Speed**: Tests run in milliseconds, not seconds
- **Reliability**: No dependency on external services or system state
- **Isolation**: Each test focuses on specific functionality
- **Determinism**: Consistent results across different environments

## Test Results Interpretation

### ✅ Success Indicators
- All tests pass without errors
- Performance tests complete within time limits
- No unexpected warnings or exceptions
- Context assembly produces valid JSON output

### ❌ Failure Indicators
- Import errors suggest missing injection modules
- Mock assertion failures indicate incorrect API usage
- Timeout failures suggest performance regression
- SystemExit with non-zero code indicates handler crashes

### ⚠️ Warning Indicators
- Pytest marker warnings (cosmetic, can be ignored)
- Missing optional dependencies
- Skipped system tests (expected if not in git repo)

## Extending the Test Suite

### Adding New Injection Module Tests
1. Create new test method in `TestInjectionModules` class
2. Add `@pytest.mark.unit` marker
3. Mock all external dependencies
4. Test success cases, edge cases, and error conditions

### Adding Integration Tests
1. Add method to `TestIntegration` class
2. Use `@pytest.mark.integration` marker
3. Mock multiple modules working together
4. Test data flow and context assembly

### Adding Performance Tests
1. Add method to `TestPerformance` class
2. Use `@pytest.mark.performance` marker
3. Include timing assertions
4. Test resource usage if applicable

## Best Practices

### When Running Tests
- **Development**: Run unit tests frequently during development
- **Pre-commit**: Run all tests except system tests
- **Release**: Run full test suite including system tests
- **Debug**: Use `-x` flag to stop on first failure for faster debugging

### Test Maintenance
- Update mocks when injection module APIs change
- Add tests for new injection modules immediately
- Keep test data realistic but minimal
- Document any test-specific environment requirements

## Troubleshooting

### Common Issues

**Import Errors**
```bash
ModuleNotFoundError: No module named 'UserPromptSubmit.xxx_injection'
```
Solution: Ensure all injection modules exist and are properly named

**Mock Assertion Failures**
```bash
AssertionError: Expected call not found
```
Solution: Check that mocked functions are called with expected parameters

**Performance Test Failures**
```bash
AssertionError: Context assembly took 2.34s, expected < 1.0s
```
Solution: Check for blocking operations or inefficient code in injection modules

**Environment Variable Issues**
```bash
KeyError: 'CLAUDE_PROJECT_DIR'
```
Solution: Ensure environment variables are properly mocked in tests

### Debug Mode
```bash
# Run with maximum verbosity and debugging
pytest hook_test.py -vv --tb=long --capture=no

# Run specific failing test in isolation
pytest hook_test.py::TestClass::test_method -vv --tb=long
```

## Integration with Hooks System

This test suite validates the complete UserPromptSubmit hook workflow:

1. **Input Processing**: Tests prompt and environment variable handling
2. **Injection Execution**: Verifies all 14 injection modules work correctly
3. **Context Assembly**: Tests string concatenation and formatting
4. **AI Optimization**: Validates OpenRouter API integration and fallbacks
5. **Output Generation**: Tests JSON response format and structure

The test suite ensures the hook system provides reliable, fast, and comprehensive context injection for every Claude prompt.

## Performance Benchmarks

### Target Performance (without AI optimization):
- **Context assembly**: < 1 second
- **Individual injections**: < 100ms each
- **Memory usage**: < 50MB additional

### Target Performance (with AI optimization):
- **Total time**: < 4 seconds (including 3s timeout)
- **Fallback time**: < 500ms if API fails
- **Network timeout**: 3 seconds maximum

These benchmarks ensure the hook system doesn't significantly slow down prompt processing while providing maximum context value.