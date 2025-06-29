"""Energy Data Service main module."""

import logging
import logging.config
import os
from pathlib import Path


def setup_logging() -> None:
    """Setup logging configuration."""
    config_path = Path(__file__).parent / "config" / "logging.ini"

    if config_path.exists():
        logging.config.fileConfig(config_path, disable_existing_loggers=False)
    else:
        logging.basicConfig(level=logging.INFO)


setup_logging()
log = logging.getLogger(__name__)


def main() -> None:
    """Main function for the energy data service."""
    log.info("Hello from energy_data_service!")


if __name__ == "__main__":
    main()
