"""
Polling-only entry point for problematic environments (like Replit)
This version skips webhook setup entirely and uses only polling
"""

import asyncio
import logging
import sys

# Apply nest_asyncio for environments that need it
try:
    import nest_asyncio
    nest_asyncio.apply()
    logging.info("✅ Applied nest_asyncio")
except ImportError:
    logging.info("ℹ️ nest_asyncio not available")

from telegram.ext import ApplicationBuilder
from src.config import config
from main import setup_logging, register_handlers
import db

async def run_polling_bot():
    """Run bot in polling-only mode"""
    logging.info("=== QUIZ BOT STARTING (POLLING ONLY) ===")
    logging.info(f"Python version: {sys.version}")
    
    # Initialize database
    logging.info("Initializing database...")
    try:
        db.init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        sys.exit(1)
    
    # Validate OpenAI key
    try:
        config.load_openai_key()
        logging.info("OpenAI API key loaded successfully")
    except ValueError as e:
        logging.error(f"OpenAI configuration error: {e}")
        sys.exit(1)
    
    # Create application
    logging.info("Creating Telegram application...")
    try:
        app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
        logging.info("Telegram application created successfully")
    except Exception as e:
        logging.error(f"Failed to create Telegram application: {e}")
        sys.exit(1)
    
    # Register handlers
    logging.info("Registering handlers...")
    register_handlers(app)
    logging.info("Handlers registered successfully")
    
    # Clear any existing webhooks
    try:
        logging.info("🧹 Clearing any existing webhooks...")
        await app.bot.delete_webhook()
        logging.info("✅ Webhooks cleared")
    except Exception as e:
        logging.warning(f"⚠️ Could not clear webhooks: {e}")
    
    # Start polling only
    logging.info("📡 Starting polling mode (webhook disabled)...")
    try:
        await app.run_polling(
            drop_pending_updates=True,
            close_loop=False  # Don't close the loop in nested environments
        )
    except Exception as e:
        logging.error(f"❌ Polling failed: {e}")
        raise
    
    logging.info("Bot stopped")

def main():
    """Entry point for polling-only mode"""
    setup_logging()
    logging.info("🔧 Using polling-only mode for maximum compatibility")
    
    try:
        asyncio.run(run_polling_bot())
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()