# Trigger Injection Monitoring & Analytics

The enhanced trigger injection system includes comprehensive monitoring to help refine keyword patterns over time.

## Unmatched Prompt Logging

Prompts that don't match any tools are automatically logged to:
```
.claude/hooks/hook_logs/trigger_misses.json
```

### Log Format
```json
[
  {
    "timestamp": "2024-01-15T10:30:45",
    "prompt": "Calculate the square root of 144",
    "words": ["calculate", "the", "square", "root", "of", "144"]
  }
]
```

### Analyzing Logs

To find common unmatched patterns:

```python
import json
from collections import Counter

# Load logs
with open('.claude/hooks/hook_logs/trigger_misses.json', 'r') as f:
    logs = json.load(f)

# Find most common words in unmatched prompts
all_words = []
for entry in logs:
    all_words.extend(entry['words'])

common_words = Counter(all_words).most_common(20)
print("Most common words in unmatched prompts:")
for word, count in common_words:
    print(f"  {word}: {count}")
```

## Negative Pattern Exclusions

Prevents false positives by excluding tools when certain phrases appear:

### Examples
- "not an issue" → excludes GitHub tool
- "simple task" → excludes ZEN analysis
- "search code" → excludes web search (prefers code search)

### Configuration
```json
{
  "mcp_mappings": {
    "mcp__github__": {
      "negative_patterns": [
        "no issue",
        "not an issue", 
        "without github",
        "avoid github"
      ]
    }
  }
}
```

## Tool Combination Patterns

Detects complex workflows that benefit from multiple tools:

### Built-in Patterns

1. **GitHub Workflow** (+20 boost)
   - "create pull request and review"
   - "merge and deploy github"
   - Suggests: GitHub + ZEN

2. **Python Debugging** (+15 boost)
   - "debug python error"
   - "fix python bug"

3. **Architecture Planning** (+25 boost)
   - "design system architecture"
   - "architect scalable solution"
   - Suggests: ZEN + Filesystem + GitHub

4. **Migration Projects** (+20 boost)
   - "migrate database schema"
   - "refactor legacy code"
   - Suggests: ZEN + Filesystem + 

### Custom Patterns
```json
{
  "tool_combinations": {
    "custom_workflow": {
      "patterns": ["specific.*pattern.*match"],
      "tools": ["mcp__tool1__", "mcp__tool2__"],
      "boost": 15
    }
  }
}
```

## Monitoring Dashboard Script

Create this script to analyze your trigger performance:

```python
#!/usr/bin/env python3
"""Analyze trigger injection performance."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

class TriggerAnalytics:
    def __init__(self):
        self.log_dir = Path(".claude/hooks/hook_logs")
        self.misses_log = self.log_dir / "trigger_misses.json"
    
    def analyze_misses(self, days=7):
        """Analyze missed triggers from the last N days."""
        if not self.misses_log.exists():
            print("No misses log found")
            return
        
        with open(self.misses_log, 'r') as f:
            logs = json.load(f)
        
        # Filter by date
        cutoff = datetime.now() - timedelta(days=days)
        recent_logs = []
        for log in logs:
            log_date = datetime.fromisoformat(log['timestamp'])
            if log_date > cutoff:
                recent_logs.append(log)
        
        print(f"\nAnalyzing {len(recent_logs)} unmatched prompts from last {days} days:")
        
        # Common words
        word_counts = Counter()
        for log in recent_logs:
            word_counts.update(log['words'])
        
        print("\nTop 15 words in unmatched prompts:")
        for word, count in word_counts.most_common(15):
            if len(word) > 2:  # Skip short words
                print(f"  {word}: {count}")
        
        # Common phrases (bigrams)
        bigrams = Counter()
        for log in recent_logs:
            words = log['words']
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                bigrams[bigram] += 1
        
        print("\nTop 10 phrases in unmatched prompts:")
        for phrase, count in bigrams.most_common(10):
            if count > 1:
                print(f"  {phrase}: {count}")
        
        # Show some examples
        print("\nRecent unmatched examples:")
        for log in recent_logs[-5:]:
            print(f"  - {log['prompt'][:60]}...")
    
    def suggest_keywords(self):
        """Suggest new keywords based on common misses."""
        # This would analyze patterns and suggest additions
        print("\nSuggested keyword additions:")
        print("  - Add 'calculate' to mcp__zen__ for math operations")
        print("  - Add 'weather' pattern to mcp__tavily-remote__")
        # etc.

if __name__ == "__main__":
    analytics = TriggerAnalytics()
    analytics.analyze_misses(days=30)
    analytics.suggest_keywords()
```

## Best Practices

1. **Review logs weekly** - Check unmatched prompts for patterns
2. **Test negative patterns** - Ensure they don't over-exclude
3. **Balance specificity** - Too broad = false positives, too narrow = misses
4. **Use combination patterns** - For workflows that naturally use multiple tools
5. **Document custom patterns** - Explain why specific patterns were added

## Metrics to Track

- **Hit rate**: % of prompts that match at least one tool
- **False positive rate**: Tools suggested but not used
- **Combination effectiveness**: How often multi-tool patterns are correct
- **Top missed patterns**: Most common unmatched prompt types

## Continuous Improvement

1. Export misses log monthly for analysis
2. Update keywords based on common patterns
3. Add negative patterns for consistent false positives
4. Create combination patterns for repeated workflows
5. Share improvements back to the team