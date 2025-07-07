#!/usr/bin/env python3
"""
Polling-only test version of Quiz Bot
"""

import asyncio
import logging
import sys
import os

# Fix for Replit and other environments with existing event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters
)

from src.config import config
from src.handlers import (
    start_command, next_command, exit_command, stop_command,
    news_command, stat_command, lang_command, debug_command,
    mode_callback, difficulty_callback, rounds_callback,
    questions_callback, time_callback, join_callback,
    end_registration_callback, captain_callback, answer_callback,
    next_round_callback, show_rating_callback, leave_callback,
    theme_message_handler, answer_message_handler, lang_choice_handler
)
from src.utils.filters import THEME_STAGE_FILTER, ANSWER_STAGE_FILTER, LANGUAGE_STAGE_FILTER
import db

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def register_handlers(app):
    """Register all bot handlers"""
    # Command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('next', next_command))
    app.add_handler(CommandHandler('exit', exit_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('news', news_command))
    app.add_handler(CommandHandler('stat', stat_command))
    app.add_handler(CommandHandler('lang', lang_command))
    app.add_handler(CommandHandler('debug', debug_command))
    
    # Unified settings handler
    try:
        from src.handlers.callbacks import unified_settings_callback
        app.add_handler(CallbackQueryHandler(unified_settings_callback, pattern='^unified_'))
        logging.info("✅ Unified settings handler registered")
    except ImportError as e:
        logging.warning(f"⚠️ Could not import unified handler: {e}")
    
    # Other callback handlers
    app.add_handler(CallbackQueryHandler(mode_callback, pattern='^mode_'))
    app.add_handler(CallbackQueryHandler(difficulty_callback, pattern='^difficulty_'))
    app.add_handler(CallbackQueryHandler(rounds_callback, pattern='^rounds_'))
    app.add_handler(CallbackQueryHandler(questions_callback, pattern='^questions_'))
    app.add_handler(CallbackQueryHandler(time_callback, pattern='^time_'))
    app.add_handler(CallbackQueryHandler(join_callback, pattern='^join$'))
    app.add_handler(CallbackQueryHandler(end_registration_callback, pattern='^end_registration$'))
    app.add_handler(CallbackQueryHandler(captain_callback, pattern='^captain_'))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern='^answer$'))
    app.add_handler(CallbackQueryHandler(next_round_callback, pattern='^next_round$'))
    app.add_handler(CallbackQueryHandler(show_rating_callback, pattern='^show_rating$'))
    app.add_handler(CallbackQueryHandler(leave_callback, pattern='^leave$'))
    
    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & THEME_STAGE_FILTER, 
        theme_message_handler
    ))
    app.add_handler(MessageHandler(
        filters.REPLY & filters.TEXT & ~filters.COMMAND, 
        answer_message_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & LANGUAGE_STAGE_FILTER, 
        lang_choice_handler
    ))

async def main():
    """Main function for polling-only bot"""
    setup_logging()
    
    logging.info("=== QUIZ BOT POLLING TEST ===")
    
    # Initialize database
    db.init_db()
    logging.info("Database initialized")
    
    # Load OpenAI key
    try:
        config.load_openai_key()
        logging.info("OpenAI key loaded")
    except ValueError as e:
        logging.warning(f"OpenAI key not found: {e}")
    
    # Create application
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    logging.info("Application created")
    
    # Register handlers
    register_handlers(app)
    logging.info("Handlers registered")
    
    # Clear webhook and start polling
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        logging.info("✅ Webhook cleared, pending updates dropped")
    except Exception as e:
        logging.warning(f"Could not clear webhook: {e}")
    
    # Start polling
    logging.info("🚀 Starting polling mode...")
    try:
        await app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logging.info("Bot stopped")
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    # Set environment variable if not set
    if not os.getenv('TELEGRAM_TOKEN'):
        os.environ['TELEGRAM_TOKEN'] = '8082065832:AAFMg57PUuHJzTt2YavoqCK5pEBYlhpVdYg'
    
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # Use nest_asyncio approach
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise