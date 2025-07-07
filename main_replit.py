"""
Alternative entry point for Replit environment
Use this if main.py has event loop issues
"""

import asyncio
import logging
import sys

# Apply nest_asyncio for Replit
import nest_asyncio
nest_asyncio.apply()

from main import setup_logging, run_bot

async def main_async():
    """Async entry point for Replit"""
    setup_logging()
    logging.info("🔧 Using Replit-specific entry point")
    await run_bot()

def main():
    """Replit-specific main function"""
    try:
        # This should work in Replit with nest_asyncio
        asyncio.run(main_async())
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()