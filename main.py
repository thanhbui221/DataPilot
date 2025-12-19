#!/usr/bin/env python3
"""DataPilot - AI Data Analyst Agent (Telegram Bot)"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.bot.telegram_bot import DataPilotBot
import logging

logger = logging.getLogger("datapilot")


def main():
    """Main entry point."""
    try:
        bot = DataPilotBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

