#!/usr/bin/env python3
"""Demo script showing dynamic suffix injection behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent / "hook_handlers" / "UserPromptSubmit")
)

from suffix_injection import get_suffix


def demo_prompts():
    """Show how suffix adapts to different prompts."""
    demo_cases = [
        ("Simple calculation", "what is 2 + 2?"),
        ("Debugging task", "debug the memory leak in the payment processing module"),
        (
            "Architecture design",
            "design a scalable event-driven architecture for real-time analytics",
        ),
        (
            "Security fix",
            "fix the SQL injection vulnerability in the user input validation",
        ),
        (
            "Performance optimization",
            "optimize the database queries to reduce page load time",
        ),
    ]

    print("=== Suffix Injection Demo ===\n")
    print(
        "The '3 Next Steps' requirement is ALWAYS included, plus context-aware enhancements.\n"
    )

    for title, prompt in demo_cases:
        print(f"\n{'=' * 60}")
        print(f"{title}: '{prompt}'")
        print("=" * 60)

        suffix = get_suffix(prompt)

        # Extract just the unique parts for readability
        lines = suffix.split("\n")
        sections = []
        current_section = []

        for line in lines:
            if line.strip().startswith("<") and line.strip().endswith(">"):
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        for section in sections:
            if section.strip():
                print(f"\n{section}")


if __name__ == "__main__":
    demo_prompts()
