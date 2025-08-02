#!/usr/bin/env python3
"""Test that configuration extraction works correctly."""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hook_handlers.UserPromptSubmit.ai_context_optimizer import AIContextOptimizer


def test_config_loading():
    """Test that all new configuration sections are loaded correctly."""
    print("Testing configuration loading...")

    optimizer = AIContextOptimizer()

    # Test logging config
    assert "logging" in optimizer.config
    assert optimizer.config["logging"]["level"] == "DEBUG"
    assert "format" in optimizer.config["logging"]
    print("✓ Logging configuration loaded")

    # Test API config
    assert "api" in optimizer.config
    assert "headers" in optimizer.config["api"]
    assert optimizer.config["api"]["headers"]["Content-Type"] == "application/json"
    print("✓ API configuration loaded")

    # Test context detection config
    assert "context_detection" in optimizer.config
    assert "tags" in optimizer.config["context_detection"]
    assert "<lsp-diagnostics>" in optimizer.config["context_detection"]["tags"]
    print("✓ Context detection configuration loaded")

    # Test display config
    assert "display" in optimizer.config
    assert optimizer.config["display"]["max_context_sections"] == 5
    assert "truncation_marker" in optimizer.config["display"]
    print("✓ Display configuration loaded")

    # Test output formats config
    assert "output_formats" in optimizer.config
    assert "fallback_template" in optimizer.config["output_formats"]
    assert "context_prefix" in optimizer.config["output_formats"]
    print("✓ Output formats configuration loaded")

    print("✅ All configuration sections loaded successfully!")


def test_config_usage():
    """Test that configuration values are actually being used."""
    print("\nTesting configuration usage...")

    optimizer = AIContextOptimizer()

    # Test a simple fallback optimization to ensure config is used
    result = optimizer._fallback_optimization(
        "Fix this error",
        "Error in authentication system",
    )

    # Should contain the questionnaire
    assert "=== CLAUDE CODE META ANALYSIS ===" in result
    assert "1. Confidence Level:" in result
    print("✓ Configuration being used in optimization")

    print("✅ Configuration usage test passed!")


if __name__ == "__main__":
    test_config_loading()
    test_config_usage()
    print("\n🎉 All configuration extraction tests passed!")
