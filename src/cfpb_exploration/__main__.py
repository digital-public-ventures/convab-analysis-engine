"""Entry point for running cfpb-exploration as a module: python -m cfpb-exploration"""
import sys
from .logging import logger


def main() -> int:
    """Main entry point for the application."""
    logger.info("Starting cfpb-exploration")

    # Your application logic here
    print("Hello from cfpb-exploration!")
    print("Edit src/cfpb-exploration/__main__.py to customize this entry point.")

    logger.info("cfpb-exploration completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
