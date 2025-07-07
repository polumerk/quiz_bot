#!/usr/bin/env python3
"""
Forced polling version of Quiz Bot
"""

import os
import sys

# Force environment
os.environ['TELEGRAM_TOKEN'] = '8082065832:AAFMg57PUuHJzTt2YavoqCK5pEBYlhpVdYg'

# Import main but modify for polling only
from main import main, run_bot, register_handlers, setup_logging
from src.config import config
from telegram.ext import ApplicationBuilder
import db
import asyncio
import logging

async def run_polling_bot():
    """Force polling mode"""
    logging.info("=== QUIZ BOT FORCED POLLING ===")
    
    # Initialize database
    db.init_db()
    logging.info("Database initialized")
    
    # Load OpenAI key (optional)
    try:
        config.load_openai_key()
        logging.info("OpenAI API key loaded")
    except ValueError:
        logging.warning("OpenAI key not found - continuing without it")
    
    # Create application
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    logging.info("Application created")
    
    # Register handlers
    register_handlers(app)
    logging.info("Handlers registered")
    
    # Force clear webhook
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        logging.info("✅ Webhook cleared, starting polling...")
    except Exception as e:
        logging.warning(f"Could not clear webhook: {e}")
    
    # Start polling only
    logging.info("🚀 Starting FORCED polling mode...")
    await app.run_polling(drop_pending_updates=True)

def main_polling():
    """Main entry point for forced polling"""
    setup_logging()
    
    try:
        asyncio.run(run_polling_bot())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            logging.info("Using nest_asyncio for existing event loop")
            import nest_asyncio
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_polling_bot())
        else:
            raise
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")

if __name__ == "__main__":
    main_polling()