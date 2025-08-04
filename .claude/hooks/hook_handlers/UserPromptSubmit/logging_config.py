"""Logging configuration that forces all output to stderr.

Overrides print statements and configures all loggers to use stderr only.
"""

import logging
import sys


class StderrHandler(logging.StreamHandler):
    """Custom handler that always uses stderr."""

    def __init__(self):
        super().__init__(sys.stderr)


class StderrOnlyFilter(logging.Filter):
    """Filter that ensures all log records go to stderr."""

    def filter(self, record: logging.LogRecord) -> bool:
        return True


def configure_stderr_logging():
    """Configure all logging to go to stderr only."""

    # Remove all existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stderr handler with detailed formatting
    stderr_handler = StderrHandler()
    stderr_handler.setLevel(logging.DEBUG)

    # Set detailed formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stderr_handler.setFormatter(formatter)

    # Add filter to ensure stderr only
    stderr_handler.addFilter(StderrOnlyFilter())

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stderr_handler)

    # Ensure no propagation to higher level loggers
    root_logger.propagate = False


def redirect_stdout_to_stderr():
    """Redirect sys.stdout to sys.stderr to catch print statements."""
    # sys.stdout = sys.stderr  # Commented out - prevents JSON output to stdout


def override_print():
    """Override built-in print to always use stderr."""
    import builtins

    original_print = builtins.print

    def stderr_print(*args, **kwargs):
        kwargs["file"] = sys.stderr
        return original_print(*args, **kwargs)

    builtins.print = stderr_print


def setup_module_loggers():
    """Configure specific module loggers to use stderr."""

    # List of modules that might need explicit configuration
    modules = [
        "UserPromptSubmit",
        "context_manager",
        "context_revival",
        "firecrawl_injection",
        "git_injection",
        "mcp_injector",
        "session_state",
        "static_content",
        "system_monitor",
        "unified_smart_advisor",
    ]

    for module_name in modules:
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Ensure it uses the root logger configuration
        logger.propagate = True


def initialize_stderr_logging():
    """Initialize complete stderr-only logging configuration."""

    # Step 1: Configure stderr logging
    configure_stderr_logging()

    # Step 2: Redirect stdout to stderr
    redirect_stdout_to_stderr()

    # Step 3: Override print function
    # override_print()  # Commented out to allow JSON to go to stdout

    # Step 4: Setup module loggers
    setup_module_loggers()

    # Log configuration completion
    logger = logging.getLogger(__name__)
    logger.info("Stderr-only logging configuration initialized")


# Auto-initialize when module is imported
initialize_stderr_logging()
