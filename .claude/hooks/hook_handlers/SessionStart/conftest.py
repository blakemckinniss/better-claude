"""Pytest configuration and fixtures for SessionStart tests."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def _run_git_command(cmd: list, cwd: str) -> None:
    """Safely run git commands using subprocess."""
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def temp_git_repo() -> Generator[str, None, None]:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()
        
        # Initialize git repo
        _run_git_command(["git", "init"], str(repo_path))
        _run_git_command(["git", "config", "user.email", "test@example.com"], str(repo_path))
        _run_git_command(["git", "config", "user.name", "Test User"], str(repo_path))
        
        # Create some test files
        (repo_path / "README.md").write_text("# Test Repository\nThis is a test.")
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("print('Hello, World!')")
        (repo_path / "tests").mkdir()
        (repo_path / "tests" / "test_main.py").write_text("def test_example(): pass")
        (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/\n.pytest_cache/")
        
        # Initial commit
        _run_git_command(["git", "add", "."], str(repo_path))
        _run_git_command(["git", "commit", "-m", "Initial commit"], str(repo_path))
        
        # Add another commit
        (repo_path / "src" / "utils.py").write_text("def helper(): return 42")
        _run_git_command(["git", "add", "."], str(repo_path))
        _run_git_command(["git", "commit", "-m", "Add utils module"], str(repo_path))
        
        yield str(repo_path)


@pytest.fixture
def empty_git_repo() -> Generator[str, None, None]:
    """Create an empty git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "empty_repo"
        repo_path.mkdir()
        
        _run_git_command(["git", "init"], str(repo_path))
        _run_git_command(["git", "config", "user.email", "test@example.com"], str(repo_path))
        _run_git_command(["git", "config", "user.name", "Test User"], str(repo_path))
        
        yield str(repo_path)


@pytest.fixture
def non_git_dir() -> Generator[str, None, None]:
    """Create a temporary directory without git initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        (Path(temp_dir) / "file.txt").write_text("test content")
        yield temp_dir


@pytest.fixture
def large_git_repo() -> Generator[str, None, None]:
    """Create a larger git repository for performance testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "large_repo"
        repo_path.mkdir()
        
        _run_git_command(["git", "init"], str(repo_path))
        _run_git_command(["git", "config", "user.email", "test@example.com"], str(repo_path))
        _run_git_command(["git", "config", "user.name", "Test User"], str(repo_path))
        
        # Create many files and directories
        for i in range(10):
            subdir = repo_path / f"module_{i}"
            subdir.mkdir()
            for j in range(20):
                (subdir / f"file_{j}.py").write_text(f"# Module {i} File {j}\nprint('{i}-{j}')")
        
        _run_git_command(["git", "add", "."], str(repo_path))
        _run_git_command(["git", "commit", "-m", "Initial large commit"], str(repo_path))
        
        yield str(repo_path)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess operations for reliable testing."""
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Default successful process mock
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"success output", b"")
        process_mock.returncode = 0
        mock_subprocess.return_value = process_mock
        yield mock_subprocess


@pytest.fixture
def mock_git_cache():
    """Mock the GitCache for testing."""
    with patch('SessionStart.git_operations.GitCache') as mock_cache:
        cache_instance = MagicMock()
        cache_instance.get.return_value = None
        cache_instance.set.return_value = None
        cache_instance.is_expired.return_value = True
        mock_cache.return_value = cache_instance
        yield cache_instance


@pytest.fixture
def mock_subprocess_pool():
    """Mock the SubprocessPool for testing."""
    with patch('SessionStart.git_operations.SubprocessPool') as mock_pool:
        pool_instance = AsyncMock()
        pool_instance.get_connection.return_value = AsyncMock()
        pool_instance.return_connection.return_value = None
        pool_instance.cleanup.return_value = None
        mock_pool.return_value = pool_instance
        yield pool_instance


@pytest.fixture
def sample_input_data() -> Dict[str, Any]:
    """Sample input data for SessionStart handler."""
    return {
        "session_id": "test_session_123",
        "message": "Test message",
        "timestamp": "2024-01-01 12:00:00",
        "project_dir": "/test/project",
    }


@pytest.fixture
def sample_context_data() -> Dict[str, Any]:
    """Sample context data returned by gather functions."""
    return {
        "readme_content": "# Test Project\nA test project.",
        "project_metadata": {
            "name": "test-project",
            "language": "Python",
            "total_files": 42,
        },
        "git_status": "On branch main\nnothing to commit",
        "recent_commits": "abc123 Initial commit\ndef456 Add feature",
        "project_structure": "src/\n  main.py\ntests/",
        "tracked_files": ["src/main.py", "tests/test_main.py"],
        "file_type_summary": {"py": 15, "md": 3, "txt": 2},
    }


@pytest.fixture
def mock_environment_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "CLAUDE_SESSION_START_MODE": "fast",
        "CLAUDE_CACHE_TTL": "30",
        "CLAUDE_DEBUG": "false",
        "CLAUDE_DISABLE_GIT": "false",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


class AsyncContextManagerMock:
    """Helper class for mocking async context managers."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        
    async def __aenter__(self):
        return self.return_value
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_context_mock():
    """Factory for creating async context manager mocks."""
    return AsyncContextManagerMock
