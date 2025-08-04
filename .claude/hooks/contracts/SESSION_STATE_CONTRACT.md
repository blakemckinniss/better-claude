# Session State Contract

## Purpose
This contract governs session state management, context revival mechanisms, and data persistence within the better-claude system. This contract is HIGH priority for ensuring seamless user experience across session boundaries and system restarts.

## Core Principles

### 1. Context Revival Architecture

#### 1.1 State Persistence Layers
```json
{
  "persistence": {
    "memory": "active_session_data",
    "disk": "session_snapshots", 
    "cache": "frequently_accessed_context",
    "backup": "disaster_recovery_state"
  }
}
```

#### 1.2 Context Priority Classification
- **Critical**: Active file modifications, uncommitted changes
- **Important**: Recent command history, user preferences
- **Useful**: Project context, cached computations
- **Optional**: Diagnostic data, performance metrics

#### 1.3 Revival Trigger Points
- System restart after unexpected shutdown
- Session timeout recovery
- Context size limit exceeded
- User-initiated session restoration

### 2. Session Continuity Standards

#### 2.1 State Preservation Requirements
- **File changes**: 100% accuracy, zero data loss
- **Command history**: Last 100 commands preserved
- **Project context**: Current working directory, git state
- **User preferences**: Settings, tool configurations

#### 2.2 Seamless Transition Criteria
```
- Context restoration: <2s for typical sessions
- Data integrity: 100% for critical data
- User notification: Clear status during recovery
- Fallback options: Graceful degradation if recovery fails
```

### 3. Data Integrity Validation

#### 3.1 Checksum Verification
- SHA-256 hashes for critical file states
- Incremental checksums for large context data
- Cross-validation between memory and disk state
- Automatic corruption detection and repair

#### 3.2 Consistency Checks
- State timestamp validation
- Cross-reference verification between components
- Dependency graph consistency validation
- User action sequence integrity

### 4. State Synchronization

#### 4.1 Multi-Component Sync
- File system state synchronization
- Git repository state tracking
- Tool state preservation (rg, fd, etc.)
- External service connection state

#### 4.2 Conflict Resolution
- Last-write-wins for user preferences  
- Merge strategies for concurrent modifications
- User prompt for critical conflicts
- Automatic rollback for irreconcilable states

## Implementation Requirements

### 1. State Storage Architecture

#### 1.1 Storage Strategy
```json
{
  "session_storage": {
    "format": "compressed_json",
    "location": "~/.claude/sessions/",
    "retention": "30_days",
    "backup_frequency": "every_10_minutes"
  }
}
```

#### 1.2 Data Serialization
- JSON for structured data with schema validation
- Binary format for large binary data
- Compression for repetitive context data
- Encryption for sensitive information

### 2. Recovery Mechanisms

#### 2.1 Automatic Recovery
- Boot-time session restoration
- Periodic state snapshotting during operation
- Crash recovery with last known good state
- Progressive context rebuilding if needed

#### 2.2 Manual Recovery Options
- User-initiated session restore from specific timestamp
- Selective context recovery (files, preferences, etc.)
- Export/import session state for debugging
- Reset to clean state with user confirmation

### 3. Context Size Management

#### 3.1 Intelligent Pruning
- LRU-based context eviction
- Importance-weighted retention scoring
- User activity pattern learning
- Automatic compression of old context

#### 3.2 Context Segmentation
- Active working set (high priority)
- Recent history (medium priority)  
- Background context (low priority)
- Archive storage (cold storage)

## Validation Criteria

### 1. Recovery Success Metrics

#### 1.1 Data Integrity Validation
- **Zero data loss**: 100% for critical state
- **Context accuracy**: >99% for working context
- **Preference preservation**: 100% for user settings
- **Command history**: >95% accuracy for recent commands

#### 1.2 Performance Requirements
- Session restore time: <3s for typical workloads
- State snapshot time: <500ms background operation
- Memory overhead: <50MB for state management
- Disk usage: <100MB per active session

### 2. Reliability Standards

#### 2.1 Recovery Success Rate
- **Normal shutdown**: 100% successful recovery
- **Abnormal termination**: >99% successful recovery
- **System crash**: >95% successful recovery
- **Corruption detection**: 100% with automatic repair

#### 2.2 User Experience Validation
- Transparent recovery (user unaware of process)
- Clear status communication during recovery
- Fallback options when recovery fails
- User control over recovery behavior

### 3. Stress Testing Requirements

#### 3.1 Failure Scenarios
- Power loss during active operations
- Disk full during state persistence
- Corrupt session files
- Network interruption during cloud sync

#### 3.2 Scale Testing
- Large context sizes (>100MB)
- Long-running sessions (>24 hours)
- Multiple concurrent sessions
- Rapid session switching

## Enforcement

### 1. Automated Safeguards

#### 1.1 State Validation
- Real-time integrity checking
- Automatic backup verification
- Corrupt state detection and isolation
- Recovery process monitoring

#### 1.2 Preventive Measures
- Regular state health checks
- Proactive cleanup of stale data
- Storage space monitoring and management
- Performance impact monitoring

### 2. Violation Response

#### 2.1 Data Integrity Issues
- **Critical**: Immediate backup restoration
- **High**: User notification with recovery options
- **Medium**: Background repair with user notification
- **Low**: Logging with scheduled cleanup

#### 2.2 Performance Degradation
- Automatic pruning of excessive context
- User notification of storage constraints
- Graceful degradation of non-essential features
- Emergency cleanup procedures

### 3. Quality Assurance

#### 3.1 Testing Requirements
- Automated recovery testing in CI/CD
- Chaos engineering for failure scenarios
- User acceptance testing for recovery flows
- Performance regression testing

#### 3.2 Monitoring and Alerting
- Session recovery success rate monitoring
- State corruption detection alerts
- Performance degradation notifications
- Storage usage trend analysis

## Emergency Procedures

### 1. Catastrophic State Loss

#### 1.1 Immediate Response
1. Assess scope of data loss
2. Attempt recovery from backup sources
3. Notify user of situation and available options
4. Initialize clean state if recovery impossible

#### 1.2 Recovery Strategies
- Incremental recovery from partial backups
- Context reconstruction from available sources
- User-guided state rebuilding
- Import from external sources if available

### 2. State Corruption Detection

#### 2.1 Corruption Response
1. Isolate corrupted state immediately
2. Attempt repair using integrity checks
3. Fallback to last known good state
4. User notification and manual intervention if needed

#### 2.2 Prevention Enhancement
- Enhanced checksum validation
- More frequent backup intervals
- Additional redundancy for critical data
- Improved corruption detection algorithms

### 3. Performance Emergency

#### 3.1 State Bloat Management
1. Emergency context pruning
2. Archive old session data
3. Optimize state storage format
4. User notification of cleanup actions

#### 3.2 Recovery Optimization
- Parallel recovery operations where possible
- Progressive context loading
- Priority-based recovery ordering
- User control over recovery depth