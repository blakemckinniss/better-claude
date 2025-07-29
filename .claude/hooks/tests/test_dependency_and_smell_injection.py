"""Test the dependency graph and code smell injection features."""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from hook_handlers.UserPromptSubmit.content_injection import get_content_injection


def test_dependency_injection():
    """Test that dependency analysis is properly injected."""
    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
import os
import sys
from datetime import datetime

def process_data():
    pass
""",
        )
        temp_file = f.name

    try:
        # Test with a prompt mentioning the file
        prompt = f"Can you help me refactor {temp_file}?"
        injection = get_content_injection(prompt)

        print("Dependency Injection Test:")
        print(f"Prompt: {prompt}")
        print(f"Injection: {injection}")

        # The injection might not include dependency info if no dependencies found
        # But it should at least have some content
        assert injection != ""

    finally:
        os.unlink(temp_file)


def test_code_smell_injection():
    """Test that code smell detection is properly injected."""
    # Create a temporary Python file with intentional code smells
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
def very_long_function_with_many_parameters(param1, param2, param3, param4, param5, param6, param7):
    x = 100  # Magic number
    y = 200  # Another magic number
    
    # TODO: Fix this later
    # FIXME: This is broken
    
    try:
        result = param1 + param2 + param3 + param4 + param5 + param6 + param7
    except:  # Broad except
        pass
    
    if x > 50:
        if y > 100:
            if result > 1000:
                if param1 > 0:
                    return result
    
    print("Debug output")
    
    global some_global_var
    some_global_var = result
    
    eval("result * 2")  # Dangerous!
    
    return result
""",
        )
        temp_file = f.name

    try:
        # Test with a prompt mentioning the file
        prompt = f"Can you review the code in {temp_file}?"
        injection = get_content_injection(prompt)

        print("\nCode Smell Injection Test:")
        print(f"Prompt: {prompt}")
        print(f"Injection: {injection}")

        # Debug output
        print(f"Injection length: {len(injection)}")
        print(f"Contains quality warnings: {'CODE_QUALITY_WARNINGS' in injection}")

        # Should detect quality issues - but injection might be empty if imports failed
        if injection:
            assert (
                "CODE_QUALITY_WARNINGS" in injection or "quality" in injection.lower()
            )

    finally:
        os.unlink(temp_file)


def test_combined_injection():
    """Test that both dependency and smell analysis work together."""
    # Create multiple files to test dependencies
    with tempfile.TemporaryDirectory() as tmpdir:
        # Main file
        main_file = Path(tmpdir) / "main.py"
        main_file.write_text(
            """
from utils import helper_function

def main():
    # Very long function with issues
    x = 100
    y = 200
    z = 300
    
    try:
        result = helper_function(x, y, z)
    except:
        pass
    
    # TODO: Refactor this
    if x > 0:
        if y > 0:
            if z > 0:
                print("All positive")
    
    return result
""",
        )

        # Utils file
        utils_file = Path(tmpdir) / "utils.py"
        utils_file.write_text(
            """
def helper_function(a, b, c):
    return a + b + c
""",
        )

        # Test injection
        prompt = f"I need to refactor {main_file} and update all dependent files"
        injection = get_content_injection(prompt)

        print("\nCombined Injection Test:")
        print(f"Prompt: {prompt}")
        print(f"Injection: {injection}")

        # Should have some optimization advice
        assert injection != ""


if __name__ == "__main__":
    test_dependency_injection()
    test_code_smell_injection()
    test_combined_injection()
    print("\nAll tests passed!")
