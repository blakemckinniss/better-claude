"""Configuration hot-reloading utilities."""

import logging
import signal
from typing import Optional

from UserPromptSubmit.config import reload_config

logger = logging.getLogger(__name__)


def setup_config_hot_reload() -> None:
    """Setup signal handler for configuration hot-reload."""

    def reload_handler(signum: int, frame: Optional[object]) -> None:
        """Handle SIGUSR1 signal to reload configuration."""
        try:
            config = reload_config()
            logger.info(f"Configuration reloaded successfully: {config}")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

    # Register signal handler for SIGUSR1
    signal.signal(signal.SIGUSR1, reload_handler)
    logger.info("Hot-reload setup complete. Send SIGUSR1 to reload config.")


def trigger_config_reload() -> bool:
    """Programmatically trigger configuration reload."""
    try:
        reload_config()
        logger.info("Configuration reloaded programmatically")
        return True
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        return False
