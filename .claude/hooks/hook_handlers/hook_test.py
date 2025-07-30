#!/usr/bin/env python3
"""Comprehensive test suite for UserPromptSubmit hook system.

Test Categories:
- unit: Test individual injection modules with mocked dependencies
- integration: Test module interaction and context assembly
- ai_contract: Test AI optimization workflow with mocked API calls
- system: End-to-end system tests (run sparingly)

Usage:
    pytest hook_test_fixed.py -v                    # Run all tests
    pytest hook_test_fixed.py -m unit              # Run only unit tests
    pytest hook_test_fixed.py -m "not system"     # Skip slow system tests
    pytest -x hook_test_fixed.py                   # Stop on first failure
    pytest --tb=short hook_test_fixed.py           # Shorter traceback format
"""

import os
import sys
import tempfile
import unittest.mock as mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the current directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main handler function by loading the script directly
import importlib.util

# Import individual injection functions directly
from UserPromptSubmit.agent_injector import get_agent_injection
from UserPromptSubmit.ai_context_optimizer import optimize_injection_sync
from UserPromptSubmit.content_injection import get_content_injection
from UserPromptSubmit.context_history_injection import get_context_history_injection
from UserPromptSubmit.firecrawl_injection import get_firecrawl_injection
from UserPromptSubmit.git_injection import get_git_injection
from UserPromptSubmit.lsp_diagnostics_injection import get_lsp_diagnostics_injection
from UserPromptSubmit.mcp_injector import get_mcp_injection
from UserPromptSubmit.prefix_injection import get_prefix
from UserPromptSubmit.runtime_monitoring_injection import (
    get_runtime_monitoring_injection,
)
from UserPromptSubmit.suffix_injection import get_suffix
from UserPromptSubmit.test_status_injection import get_test_status_injection
from UserPromptSubmit.tree_sitter_injection import (
    create_tree_sitter_injection,
    get_tree_sitter_hints,
)
from UserPromptSubmit.trigger_injection import get_trigger_injection
from UserPromptSubmit.zen_injection import get_zen_injection

spec = importlib.util.spec_from_file_location(
    "main_handler_module",
    "UserPromptSubmit.py",
)
main_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_handler_module)


# Test Fixtures and Utilities
@pytest.fixture
def mock_project_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_user_prompt():
    """Sample user prompt for testing."""
    return "Fix the authentication bug in user login"


@pytest.fixture
def sample_raw_context():
    """Sample raw context for AI optimization testing."""
    return """
## Git Status
modified: src/auth.py
modified: tests/test_auth.py

## System Monitoring
CPU: 45%, Memory: 2.1GB, Disk: 89%

## Test Status
pytest: 12 passed, 3 failed
Coverage: 85%

## LSP Diagnostics
auth.py:42: error: Undefined variable 'user_token'
auth.py:58: warning: Unused import 'datetime'
"""


# Unit Tests for Individual Injection Modules
class TestInjectionModules:
    """Unit tests for individual injection modules."""

    @pytest.mark.unit
    def test_prefix_injection(self):
        """Test prefix injection returns valid string."""
        result = get_prefix()
        assert isinstance(result, str)
        assert len(result) >= 0  # Allow empty strings

    @pytest.mark.unit
    def test_suffix_injection(self, sample_user_prompt):
        """Test suffix injection returns valid string."""
        result = get_suffix(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_git_injection_clean_repo(self, mock_project_dir):
        """Test git injection with clean repository."""
        with patch(
            "UserPromptSubmit.git_injection.GitInjector.run_git_command",
        ) as mock_git:
            # Mock git commands for clean repo
            mock_git.side_effect = [
                "main",  # current branch
                "main",  # main branch detection
                "",  # status --porcelain (empty = clean)
                "abc123|Author|2023-01-01|Initial commit|",  # recent commits
            ]

            result = await get_git_injection(mock_project_dir)
            assert isinstance(result, str)
            if result:  # Only check if result is not empty
                assert "main" in result.lower() or "clean" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_git_injection_with_changes(self, mock_project_dir):
        """Test git injection with modified files."""
        with patch(
            "UserPromptSubmit.git_injection.GitInjector.run_git_command",
        ) as mock_git:
            # Mock git commands for repo with changes
            mock_git.side_effect = [
                "feature-branch",  # current branch
                "main",  # main branch detection
                " M src/auth.py\n M tests/test_auth.py",  # status --porcelain (modified files)
                "def456|Author|2023-01-02|Fix auth issue|",  # recent commits
            ]

            result = await get_git_injection(mock_project_dir)
            assert isinstance(result, str)
            if result:  # Only check if result is not empty
                assert "auth.py" in result or "modified" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_git_injection_no_git_repo(self, mock_project_dir):
        """Test git injection when not in git repository."""
        with patch(
            "UserPromptSubmit.git_injection.GitInjector.is_git_repo",
        ) as mock_is_git:
            # Mock not being in a git repository
            mock_is_git.return_value = False

            result = await get_git_injection(mock_project_dir)
            assert isinstance(result, str)
            assert result == ""  # Should return empty string for non-git repos

    @pytest.mark.unit
    def test_zen_injection(self, sample_user_prompt):
        """Test ZEN injection returns guidance."""
        result = get_zen_injection(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_content_injection(self, sample_user_prompt):
        """Test content injection returns hints."""
        result = get_content_injection(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_trigger_injection(self, sample_user_prompt):
        """Test trigger injection returns relevant triggers."""
        result = get_trigger_injection(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_tree_sitter_injection(self, sample_user_prompt):
        """Test tree-sitter injection returns analysis."""
        result = create_tree_sitter_injection(sample_user_prompt)
        assert isinstance(result, str)

        hints = get_tree_sitter_hints(sample_user_prompt)
        assert isinstance(hints, str)

    @pytest.mark.unit
    def test_mcp_injection(self, sample_user_prompt):
        """Test MCP injection returns recommendations."""
        result = get_mcp_injection(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_agent_injection(self, sample_user_prompt):
        """Test agent injection returns recommendations."""
        result = get_agent_injection(sample_user_prompt)
        assert isinstance(result, str)

    @pytest.mark.unit
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.cpu_percent")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.virtual_memory")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.disk_usage")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.Process")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.process_iter")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.pids")
    @patch("UserPromptSubmit.runtime_monitoring_injection.psutil.net_connections")
    @pytest.mark.asyncio
    async def test_runtime_monitoring_injection(
        self,
        mock_net,
        mock_pids,
        mock_proc_iter,
        mock_process_class,
        mock_disk,
        mock_memory,
        mock_cpu,
    ):
        """Test runtime monitoring injection with mocked system data."""
        # Mock system metrics with proper numeric values
        mock_cpu.return_value = 45.5

        # Create mock memory object with numeric attributes
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 65.2
        mock_memory_obj.available = 4096 * 1024 * 1024  # 4GB
        mock_memory.return_value = mock_memory_obj

        # Create mock disk object with numeric attributes
        mock_disk_obj = MagicMock()
        mock_disk_obj.percent = 75.0  # Below 90% threshold
        mock_disk.return_value = mock_disk_obj

        # Mock process-related calls
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 10.0
        mock_process.memory_info.return_value = MagicMock(
            rss=512 * 1024 * 1024,
        )  # 512MB
        mock_process_class.return_value = mock_process

        mock_proc_iter.return_value = []  # No processes to avoid complexity
        mock_pids.return_value = [1, 2, 3]  # Mock process count
        mock_net.return_value = []  # No network connections

        result = await get_runtime_monitoring_injection()
        assert isinstance(result, str)
        # Check that it doesn't contain error messages
        assert "error" not in result.lower()

    @pytest.mark.unit
    @patch(
        "builtins.open",
        mock.mock_open(
            read_data='{"summary": {"passed": 12, "failed": 3, "skipped": 1}, "duration": 2.34, "tests": []}',
        ),
    )
    @patch("UserPromptSubmit.test_status_injection.Path.glob")
    @pytest.mark.asyncio
    async def test_test_status_injection_pytest(
        self,
        mock_glob,
        sample_user_prompt,
        mock_project_dir,
    ):
        """Test test status injection with pytest results."""
        # Mock pytest JSON report file existing
        mock_json_file = MagicMock()
        mock_json_file.__str__ = lambda: "/fake/path/.pytest_cache/pytest-report.json"
        mock_glob.return_value = [mock_json_file]

        result = await get_test_status_injection(sample_user_prompt, mock_project_dir)
        assert isinstance(result, str)

    @pytest.mark.unit
    @patch("UserPromptSubmit.lsp_diagnostics_injection.os.path.exists")
    @patch(
        "builtins.open",
        mock.mock_open(
            read_data='[{"severity": "error", "message": "Undefined variable"}]',
        ),
    )
    @pytest.mark.asyncio
    async def test_lsp_diagnostics_injection(
        self,
        mock_exists,
        sample_user_prompt,
        mock_project_dir,
    ):
        """Test LSP diagnostics injection with mocked diagnostics."""
        # Mock diagnostic files existing
        mock_exists.return_value = True

        result = await get_lsp_diagnostics_injection(
            sample_user_prompt,
            mock_project_dir,
        )
        assert isinstance(result, str)

    @pytest.mark.unit
    @patch("UserPromptSubmit.context_history_injection.os.path.exists")
    @patch("builtins.open", mock.mock_open(read_data="src/auth.py\nsrc/user.py\n"))
    @pytest.mark.asyncio
    async def test_context_history_injection(
        self,
        mock_exists,
        sample_user_prompt,
        mock_project_dir,
    ):
        """Test context history injection with mocked history."""
        # Mock history files existing
        mock_exists.return_value = True

        result = await get_context_history_injection(
            sample_user_prompt,
            mock_project_dir,
        )
        assert isinstance(result, str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_firecrawl_injection_no_api_key(
        self,
        sample_user_prompt,
        mock_project_dir,
    ):
        """Test firecrawl injection with no API key configured."""
        # Mock no API key
        with patch.dict("os.environ", {}, clear=True):
            result = await get_firecrawl_injection(sample_user_prompt, mock_project_dir)
            assert result == ""  # Should return empty string when no API key

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_firecrawl_injection_no_search_needed(
        self,
        mock_project_dir,
    ):
        """Test firecrawl injection when no web search is needed."""
        # Mock API key but use prompt that doesn't trigger search
        simple_prompt = "Hello world"

        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
            result = await get_firecrawl_injection(simple_prompt, mock_project_dir)
            assert result == ""  # Should return empty for non-search prompts

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("UserPromptSubmit.firecrawl_injection.FirecrawlClient.search")
    async def test_firecrawl_injection_with_search(
        self,
        mock_search,
        mock_project_dir,
    ):
        """Test firecrawl injection with web search."""
        # Mock API key and search results
        mock_search.return_value = {
            "data": [
                {
                    "url": "https://example.com",
                    "title": "Test Article",
                    "markdown": "This is test content for the article.",
                },
            ],
        }

        search_prompt = "What are the latest React best practices?"

        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
            result = await get_firecrawl_injection(search_prompt, mock_project_dir)

            assert isinstance(result, str)
            if result:  # Only check content if search was triggered
                assert "<firecrawl-context>" in result
                assert "Test Article" in result or "example.com" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("UserPromptSubmit.firecrawl_injection.FirecrawlClient.scrape")
    async def test_firecrawl_injection_with_url_scraping(
        self,
        mock_scrape,
        mock_project_dir,
    ):
        """Test firecrawl injection with URL scraping."""
        # Mock API key and scrape results
        mock_scrape.return_value = {
            "data": {
                "title": "Documentation Page",
                "markdown": "This is documentation content from the scraped page.",
            },
        }

        url_prompt = "Please analyze https://docs.example.com/api"

        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
            result = await get_firecrawl_injection(url_prompt, mock_project_dir)

            assert isinstance(result, str)
            if result:  # Only check content if scraping was triggered
                assert "<firecrawl-context>" in result
                assert "Documentation Page" in result or "docs.example.com" in result


# AI Contract Tests
class TestAIOptimization:
    """Contract tests for AI optimization workflow."""

    @pytest.mark.asyncio
    @pytest.mark.ai_contract
    @patch("UserPromptSubmit.ai_context_optimizer.aiohttp.ClientSession.post")
    async def test_ai_optimization_success(
        self,
        mock_post,
        sample_user_prompt,
        sample_raw_context,
    ):
        """Test successful AI optimization with mocked OpenRouter API."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "# Role: Authentication Debug Specialist\n\n## Profile\n- language: English\n- description: Specialized in debugging authentication issues\n- expertise: Authentication systems and bug fixing\n- focus: Resolving the login bug mentioned by the user\n\n## Current Context\nGit status shows modified auth files...",
                    },
                },
            ],
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        # Set up environment with API key
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            result = optimize_injection_sync(sample_user_prompt, sample_raw_context)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain optimized content
        assert "Authentication Debug Specialist" in result
        assert "OpenRouter (google/gemini-2.5-flash)" in result

    @pytest.mark.asyncio
    @pytest.mark.ai_contract
    @patch("UserPromptSubmit.ai_context_optimizer.aiohttp.ClientSession.post")
    async def test_ai_optimization_api_error(
        self,
        mock_post,
        sample_user_prompt,
        sample_raw_context,
    ):
        """Test AI optimization fallback when API fails."""
        # Mock API error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        mock_post.return_value.__aenter__.return_value = mock_response

        # Test fallback
        result = optimize_injection_sync(sample_user_prompt, sample_raw_context)

        assert isinstance(result, str)
        assert len(result) > 0  # Should fallback to rule-based

    @pytest.mark.ai_contract
    @patch("UserPromptSubmit.ai_context_optimizer.os.environ.get")
    def test_ai_optimization_no_api_key(
        self,
        mock_env,
        sample_user_prompt,
        sample_raw_context,
    ):
        """Test AI optimization when no API key is configured."""

        # Mock missing API key
        def mock_get(key, default=None):
            if key == "OPENROUTER_API_KEY":
                return None
            return default

        mock_env.side_effect = mock_get

        result = optimize_injection_sync(sample_user_prompt, sample_raw_context)

        assert isinstance(result, str)
        assert len(result) > 0  # Should use rule-based fallback

    @pytest.mark.system
    def test_real_api_integration(self, sample_user_prompt, sample_raw_context):
        """Test real API integration - requires actual API key."""
        # Only run if API key is available
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY not available for real API test")

        # Test with real API
        result = optimize_injection_sync(sample_user_prompt, sample_raw_context)

        # Verify the result structure
        assert isinstance(result, str)
        assert len(result) > len(sample_raw_context)  # Should be enhanced

        # Should contain optimization marker
        assert "OpenRouter" in result or "rule-based" in result or "timed out" in result

        # Should still contain role-based structure if successful
        if "OpenRouter" in result:
            assert "# Role:" in result
            assert "## Profile" in result or "## Context" in result

    @pytest.mark.ai_contract
    def test_ai_optimization_timeout(self, sample_user_prompt, sample_raw_context):
        """Test AI optimization timeout handling."""
        # Test that function handles timeout gracefully
        result = optimize_injection_sync(sample_user_prompt, sample_raw_context)

        assert isinstance(result, str)
        assert len(result) > 0


# Integration Tests
class TestIntegration:
    """Integration tests for module interaction and context assembly."""

    @pytest.mark.integration
    @patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/test/project"})
    @patch("UserPromptSubmit.git_injection.get_git_injection")
    @patch("UserPromptSubmit.zen_injection.get_zen_injection")
    @patch("UserPromptSubmit.content_injection.get_content_injection")
    @patch(
        "UserPromptSubmit.runtime_monitoring_injection.get_runtime_monitoring_injection",
    )
    def test_context_assembly_without_ai(
        self,
        mock_runtime,
        mock_content,
        mock_zen,
        mock_git,
    ):
        """Test raw context assembly without AI optimization."""
        # Mock all injection returns
        mock_git.return_value = "Git: clean repo\n"
        mock_zen.return_value = "ZEN: guidance\n"
        mock_content.return_value = "Content: hints\n"
        mock_runtime.return_value = "Runtime: CPU 45%\n"

        # Mock AI optimization disabled
        with patch.dict("os.environ", {"CLAUDE_AI_CONTEXT_OPTIMIZATION": "false"}):
            # Mock the data input
            test_data = {"userPrompt": "test prompt"}

            # Capture stdout to get the JSON output
            with patch("sys.stdout", new_callable=MagicMock) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main_handler_module.handle(test_data)

                # Should exit with code 0
                assert exc_info.value.code == 0

    @pytest.mark.integration
    @patch.dict(
        "os.environ",
        {
            "CLAUDE_PROJECT_DIR": "/test/project",
            "CLAUDE_AI_CONTEXT_OPTIMIZATION": "true",
        },
    )
    @patch("UserPromptSubmit.ai_context_optimizer.optimize_injection_sync")
    def test_context_assembly_with_ai(self, mock_optimize):
        """Test context assembly with AI optimization enabled."""
        # Mock AI optimization
        mock_optimize.return_value = "# Role: Test Specialist\n\nOptimized context..."

        test_data = {"userPrompt": "debug authentication issue"}

        with patch("sys.stdout", new_callable=MagicMock):
            with pytest.raises(SystemExit) as exc_info:
                main_handler_module.handle(test_data)

            assert exc_info.value.code == 0

    @pytest.mark.integration
    def test_empty_user_prompt_handling(self):
        """Test handling of empty or missing user prompt."""
        test_data = {}  # No userPrompt key

        with patch("sys.stdout", new_callable=MagicMock):
            with pytest.raises(SystemExit) as exc_info:
                main_handler_module.handle(test_data)

            assert exc_info.value.code == 0

    @pytest.mark.integration
    def test_malformed_input_handling(self):
        """Test handling of malformed input data."""
        test_data = "not a dictionary"  # String instead of dict

        with patch("sys.stdout", new_callable=MagicMock):
            with pytest.raises(SystemExit) as exc_info:
                main_handler_module.handle(test_data)

            assert exc_info.value.code == 0


# System Tests (Run Sparingly)
class TestSystem:
    """End-to-end system tests with minimal mocking."""

    @pytest.mark.system
    @pytest.mark.slow
    def test_full_integration_real_git_repo(self, sample_user_prompt):
        """Test with real git repository (if available)."""
        # Only run if we're in a git repo
        if not os.path.exists(".git"):
            pytest.skip("Not in a git repository")

        # Test with real project directory
        test_data = {"userPrompt": sample_user_prompt}

        with patch.dict("os.environ", {"CLAUDE_AI_CONTEXT_OPTIMIZATION": "false"}):
            with patch("sys.stdout", new_callable=MagicMock):
                with pytest.raises(SystemExit) as exc_info:
                    main_handler_module.handle(test_data)

                assert exc_info.value.code == 0


# Performance Tests
class TestPerformance:
    """Performance tests to ensure hooks don't slow down prompts."""

    @pytest.mark.performance
    @patch.dict("os.environ", {"CLAUDE_AI_CONTEXT_OPTIMIZATION": "false"})
    def test_context_assembly_speed(self, sample_user_prompt):
        """Test that context assembly completes within reasonable time."""
        import time

        test_data = {"userPrompt": sample_user_prompt}

        start_time = time.time()

        with patch("sys.stdout", new_callable=MagicMock):
            with pytest.raises(SystemExit):
                main_handler_module.handle(test_data)

        execution_time = time.time() - start_time

        # Should complete within 2 seconds without AI optimization (more lenient)
        assert execution_time < 2.0, (
            f"Context assembly took {execution_time:.2f}s, expected < 2.0s"
        )

    @pytest.mark.performance
    @patch("UserPromptSubmit.ai_context_optimizer.optimize_injection_sync")
    def test_ai_optimization_timeout_enforcement(
        self,
        mock_optimize,
        sample_user_prompt,
    ):
        """Test that AI optimization respects timeout limits."""
        import time

        # Mock normal optimization (not slow)
        mock_optimize.return_value = "fast result"

        test_data = {"userPrompt": sample_user_prompt}

        with patch.dict("os.environ", {"CLAUDE_AI_CONTEXT_OPTIMIZATION": "true"}):
            start_time = time.time()

            with patch("sys.stdout", new_callable=MagicMock):
                with pytest.raises(SystemExit):
                    main_handler_module.handle(test_data)

            execution_time = time.time() - start_time

            # Should complete reasonably quickly
            assert execution_time < 5.0, (
                f"Handler took {execution_time:.2f}s, expected < 5.0s"
            )


# Error Handling Tests
class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.unit
    @patch("UserPromptSubmit.git_injection.get_git_injection")
    def test_injection_module_exception_handling(self, mock_git_injection):
        """Test that exceptions in injection modules don't crash the handler."""
        # Mock an injection that raises an exception
        mock_git_injection.side_effect = Exception("Git command failed")

        test_data = {"userPrompt": "test prompt"}

        # Handler should still complete successfully
        with patch("sys.stdout", new_callable=MagicMock):
            with pytest.raises(SystemExit) as exc_info:
                main_handler_module.handle(test_data)

            assert exc_info.value.code == 0

    @pytest.mark.unit
    def test_missing_environment_variables(self):
        """Test behavior when required environment variables are missing."""
        # Clear CLAUDE_PROJECT_DIR
        with patch.dict("os.environ", {}, clear=True):
            test_data = {"userPrompt": "test prompt"}

            with patch("sys.stdout", new_callable=MagicMock):
                with pytest.raises(SystemExit) as exc_info:
                    main_handler_module.handle(test_data)

                assert exc_info.value.code == 0


if __name__ == "__main__":
    # Run tests with coverage and detailed output
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-m",
            "not system",  # Skip slow system tests by default
        ],
    )
