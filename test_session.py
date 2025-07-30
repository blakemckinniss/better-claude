import os
import sys
sys.path.insert(0, ".claude/hooks/hook_handlers")
from UserPromptSubmit import is_first_user_prompt

print(f"Result: {is_first_user_prompt()}")

# Show what transcript files exist
import glob
transcript_dir = os.path.expanduser("~/.claude/projects")
if os.path.exists(transcript_dir):
    pattern = os.path.join(transcript_dir, "**/*.jsonl")
    files = glob.glob(pattern, recursive=True)
    print(f"\nFound {len(files)} transcript files")
    if files:
        latest = max(files, key=os.path.getmtime)
        print(f"Latest: {latest}")
        
        # Count user messages
        import json
        user_count = 0
        with open(latest) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "user":
                            user_count += 1
                    except:
                        pass
        print(f"User messages in latest transcript: {user_count}")
