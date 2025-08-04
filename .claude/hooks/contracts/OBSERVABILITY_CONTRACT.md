# Observability Contract

## Purpose
This contract establishes unified logging, monitoring, and debugging standards for the better-claude system, ensuring comprehensive visibility into system behavior, performance, and reliability. This contract is MEDIUM priority for operational excellence and troubleshooting capability.

## Core Principles

### 1. Unified Logging Architecture

#### 1.1 Log Level Hierarchy
```json
{
  "log_levels": {
    "CRITICAL": "system_failure_imminent",
    "ERROR": "operation_failed_recoverable", 
    "WARNING": "potential_issue_detected",
    "INFO": "normal_operation_events",
    "DEBUG": "detailed_execution_flow",
    "TRACE": "fine_grained_debugging"
  }
}
```

#### 1.2 Structured Logging Format
```json
{
  "timestamp": "2025-01-04T10:30:45.123Z",
  "level": "INFO",
  "component": "hook_handler",
  "event": "tool_execution",
  "tool": "rg",
  "duration_ms": 245,
  "success": true,
  "context": {
    "session_id": "sess_123",
    "user_id": "user_456",
    "operation_id": "op_789"
  }
}
```

#### 1.3 Log Routing Strategy
- **Console**: ERROR and above during development
- **File**: INFO and above with rotation (10MB, 5 files)
- **Remote**: CRITICAL and ERROR for production monitoring
- **Debug file**: DEBUG and TRACE when debugging enabled

### 2. Metrics Collection Standards

#### 2.1 System Metrics
- **Performance**: Response times, throughput, resource usage
- **Reliability**: Error rates, success rates, availability
- **Capacity**: Memory usage, disk usage, concurrent operations
- **Business**: User actions, feature usage, session metrics

#### 2.2 Custom Metrics Format
```json
{
  "metric_name": "hook_execution_duration",
  "value": 245.7,
  "unit": "milliseconds", 
  "tags": {
    "hook_type": "PreToolUse",
    "tool": "rg",
    "status": "success"
  },
  "timestamp": "2025-01-04T10:30:45.123Z"
}
```

#### 2.3 Metric Aggregation
- **Real-time**: Current values for dashboards
- **Historical**: Time series for trend analysis
- **Statistical**: P50, P95, P99 percentiles
- **Alerting**: Threshold-based notifications

### 3. Debugging Capabilities

#### 3.1 Debug Mode Features
- Verbose logging with execution traces
- Performance profiling integration
- Memory usage tracking
- Network request/response logging

#### 3.2 Diagnostic Information
```json
{
  "system_info": {
    "version": "better-claude-1.0.0",
    "python_version": "3.11.2",
    "platform": "linux-x86_64",
    "memory_available": "8GB"
  },
  "session_info": {
    "session_duration": "1h 23m",
    "commands_executed": 45,
    "tools_used": ["rg", "fd", "git"],
    "errors_encountered": 2
  }
}
```

#### 3.3 Interactive Debugging
- Real-time log streaming during operation
- Component-specific log filtering
- Performance bottleneck identification
- Error reproduction assistance

### 4. Error Tracking and Reporting

#### 4.1 Error Categorization
- **System errors**: Infrastructure and runtime failures
- **User errors**: Invalid input or usage patterns
- **Integration errors**: External tool or API failures
- **Logic errors**: Bugs in application code

#### 4.2 Error Context Capture
- Full stack traces with source locations
- Environment state at time of error
- User action sequence leading to error
- Related log entries and metrics

#### 4.3 Error Aggregation
- Error fingerprinting for deduplication
- Error frequency and trend tracking
- Impact assessment (affected users, operations)
- Resolution tracking and time-to-fix metrics

## Implementation Requirements

### 1. Logging Infrastructure

#### 1.1 Logger Configuration
```python
import logging
import structlog

# Structured logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

#### 1.2 Log Management
- Automatic log rotation based on size and age
- Compression of archived logs
- Configurable retention policies
- Log integrity verification

### 2. Monitoring Integration

#### 2.1 Metrics Export
- Prometheus-compatible metrics endpoint
- StatsD integration for real-time metrics
- Custom dashboard configuration
- Alert rule definitions

#### 2.2 Health Checks
- System component health monitoring
- Dependency availability checking
- Performance threshold monitoring
- Automated recovery trigger points

### 3. Observability Tools

#### 3.1 Development Tools
- Log viewer with filtering and search
- Real-time performance monitor
- Error rate dashboard
- Debug mode toggle

#### 3.2 Production Monitoring
- Service health dashboard
- Performance trend analysis
- Error tracking and alerting
- Capacity planning metrics

## Validation Criteria

### 1. Logging Quality

#### 1.1 Log Coverage
- **Critical paths**: 100% coverage with INFO or higher
- **Error conditions**: 100% coverage with ERROR level
- **Performance operations**: 100% coverage with timing
- **User actions**: 100% coverage with context

#### 1.2 Log Quality Standards
- All logs include necessary context
- Sensitive data properly redacted
- Log messages are actionable and clear
- Timestamps are consistent and accurate

### 2. Monitoring Effectiveness

#### 2.1 Metric Coverage
- **System resources**: CPU, memory, disk, network
- **Application performance**: Response times, throughput
- **Business metrics**: User engagement, feature usage
- **Error rates**: By component, operation type, severity

#### 2.2 Alert Responsiveness
- **Critical alerts**: <1 minute detection and notification
- **Performance alerts**: <5 minute detection
- **Trend alerts**: <1 hour for gradual degradation
- **False positive rate**: <5% of all alerts

### 3. Debugging Efficiency

#### 3.1 Problem Resolution
- **Issue reproduction**: Debug logs sufficient for 90% of issues
- **Root cause identification**: <30 minutes for typical issues
- **Error context**: Complete context captured for 100% of errors
- **Performance bottlenecks**: Identifiable through metrics

#### 3.2 User Experience
- Debug mode activation: <10 seconds
- Log search response time: <2 seconds
- Dashboard loading time: <5 seconds
- Error report generation: <30 seconds

## Enforcement

### 1. Logging Standards

#### 1.1 Code Review Requirements
- All new code includes appropriate logging
- Log levels used correctly according to guidelines
- Sensitive data redaction verified
- Log message clarity and usefulness validated

#### 1.2 Automated Checks
- Log format validation in CI/CD
- Missing log statement detection
- Sensitive data exposure scanning
- Log level consistency checking

### 2. Monitoring Compliance

#### 2.1 Metric Requirements
- All new features include relevant metrics
- Performance metrics for user-facing operations
- Error rate metrics for all failure paths
- Resource usage metrics for system operations

#### 2.2 Alert Configuration
- All critical operations have appropriate alerts
- Alert thresholds based on SLA requirements
- Alert fatigue prevention through proper tuning
- Regular alert effectiveness review

### 3. Quality Assurance

#### 3.1 Testing Requirements
- Logging functionality unit tests
- Metrics collection integration tests
- Alert trigger scenario testing
- Debug mode functionality validation

#### 3.2 Operational Validation
- Regular log analysis for insights
- Metrics trend analysis for capacity planning
- Alert response time measurement
- Debug session effectiveness review

## Emergency Procedures

### 1. Logging System Failure

#### 1.1 Immediate Response
1. Activate emergency logging fallback
2. Preserve critical system logs
3. Notify operations team of logging outage
4. Continue operation with minimal logging

#### 1.2 Recovery Procedures
- Restore primary logging system
- Recover lost log data if possible
- Validate log integrity after recovery
- Review incident for prevention improvements

### 2. Monitoring Blackout

#### 2.1 Blind Operation Protocol
1. Activate manual monitoring procedures
2. Increase logging verbosity temporarily
3. Implement basic health checks
4. Prepare for rapid response to issues

#### 2.2 System Recovery
- Restore monitoring infrastructure
- Validate metric collection accuracy
- Recalibrate alert thresholds if needed
- Conduct post-outage system review

### 3. Debug Information Overflow

#### 3.1 Resource Protection
1. Automatically disable debug mode if resources critical
2. Implement emergency log rotation
3. Clear non-essential debug data
4. Notify users of debugging limitations

#### 3.2 Optimization Response
- Optimize debug data collection efficiency
- Implement selective debugging features
- Improve log compression and storage
- Enhance debug mode resource management