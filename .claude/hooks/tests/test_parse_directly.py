#!/usr/bin/env python3
"""Test parsing directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit")
)

from suffix_injection import ClaudeMdSnippets

# Force parse
ClaudeMdSnippets._snippets_cache = None
print("Calling _parse_claude_md directly...")

try:
    snippets = ClaudeMdSnippets._parse_claude_md()
    print(f"Parse returned {len(snippets)} snippets")
    for k, v in snippets.items():
        print(f"  {k}: {len(v)} chars")
except Exception as e:
    print(f"Error during parse: {e}")
    import traceback

    traceback.print_exc()

# Check cache file
cache_path = Path(
    "/home/devcontainers/better-claude/.claude/hooks/claude_md_cache.json"
)
print(f"\nCache file exists: {cache_path.exists()}")
if cache_path.exists():
    print(f"Cache file size: {len(cache_path.read_text())} chars")
