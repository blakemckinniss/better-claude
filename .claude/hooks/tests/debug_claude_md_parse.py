#!/usr/bin/env python3
"""Debug CLAUDE.md parsing."""

import re
from pathlib import Path

claude_md_path = Path("/home/devcontainers/better-claude/CLAUDE.md")
content = claude_md_path.read_text()

print("=== Debugging CLAUDE.md Parsing ===")
print(f"File exists: {claude_md_path.exists()}")
print(f"File size: {len(content)} chars")

# Test individual patterns
patterns = [
    ("Modern Tools", r"### 1\. MODERN TOOLS ONLY.*?```bash(.*?)```", re.DOTALL),
    ("Parallel", r"### 2\. PARALLEL BY DEFAULT(.*?)(?=###|\Z)", re.DOTALL),
    ("Delegation", r"### 3\. ZEN DELEGATION MATRIX.*?(\|.*?\|.*?\n)+", re.DOTALL),
    ("Performance", r"## 🚀 PERFORMANCE RULES(.*?)(?=##|\Z)", re.DOTALL),
    ("Anti-patterns", r"## ❌ ANTI-PATTERNS(.*?)(?=##|\Z)", re.DOTALL),
]

for name, pattern, flags in patterns:
    match = re.search(pattern, content, flags)
    if match:
        preview = match.group(0)[:100].replace("\n", " ")
        print(f"\n✓ {name}: Found - {preview}...")
    else:
        print(f"\n✗ {name}: Not found")
        # Show what's around where we expect it
        if name == "Modern Tools":
            idx = content.find("MODERN TOOLS")
            if idx > -1:
                context = content[idx - 50 : idx + 200].replace("\n", " ")
                print(f"  Context: ...{context}...")
