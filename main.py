"""
Main entry point for Quiz Bot
"""

import asyncio
import logging
import os
import sys
from typing import Optional

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters
)

from src.config import config
from src.models.game_state import reset_game_state
from src.handlers import (
    start_command, next_command, exit_command, stop_command,
    news_command, stat_command, lang_command,
    mode_callback, difficulty_callback, rounds_callback,
    questions_callback, time_callback, join_callback,
    end_registration_callback, captain_callback, answer_callback,
    next_round_callback, show_rating_callback, leave_callback,
    theme_message_handler, answer_message_handler, lang_choice_handler
)
from src.utils.filters import THEME_STAGE_FILTER, ANSWER_STAGE_FILTER
from src.utils.error_handler import log_error
import db


def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('quiz_bot.log', encoding='utf-8')
        ]
    )


def register_handlers(app) -> None:
    """Register all bot handlers"""
    # Command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('next', next_command))
    app.add_handler(CommandHandler('exit', exit_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('news', news_command))
    app.add_handler(CommandHandler('stat', stat_command))
    app.add_handler(CommandHandler('lang', lang_command))
    
    # Callback query handlers
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
        filters.TEXT & ~filters.COMMAND & ANSWER_STAGE_FILTER, 
        answer_message_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        lang_choice_handler
    ))


async def setup_webhook(app) -> Optional[str]:
    """Setup webhook for deployment environments"""
    if config.is_replit_environment():
        webhook_url = config.get_replit_webhook_url()
        if webhook_url:
            webhook_path = f"/{config.TELEGRAM_TOKEN}"
            full_webhook_url = webhook_url + webhook_path
            
            logging.info(f"Setting up webhook: {full_webhook_url}")
            await app.bot.set_webhook(full_webhook_url)
            
            return webhook_path
    
    elif config.WEBHOOK_URL:
        webhook_path = f"/{config.TELEGRAM_TOKEN}"
        full_webhook_url = config.WEBHOOK_URL + webhook_path
        
        logging.info(f"Setting up webhook: {full_webhook_url}")
        await app.bot.set_webhook(full_webhook_url)
        
        return webhook_path
    
    return None


async def run_bot() -> None:
    """Main bot runner"""
    logging.info("=== QUIZ BOT STARTING ===")
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
    
    # Setup and run
    webhook_path = await setup_webhook(app)
    
    if webhook_path:
        # Webhook mode
        logging.info(f"Starting webhook server on {config.WEBHOOK_LISTEN}:{config.WEBHOOK_PORT}")
        try:
            await app.run_webhook(
                listen=config.WEBHOOK_LISTEN,
                port=config.WEBHOOK_PORT,
                url_path=webhook_path,
                webhook_url=config.WEBHOOK_URL or config.get_replit_webhook_url()
            )
        except Exception as e:
            logging.error(f"Webhook server failed: {e}")
            raise
    else:
        # Polling mode
        logging.info("Starting polling mode...")
        try:
            await app.run_polling(drop_pending_updates=True)
        except RuntimeError as e:
            if "already running" in str(e) or "Cannot close a running event loop" in str(e):
                logging.error("Event loop conflict. Cannot run in this environment.")
                sys.exit(1)
            else:
                raise
        except Exception as e:
            logging.error(f"Polling failed: {e}")
            raise
    
    logging.info("Bot stopped")


def main() -> None:
    """Entry point"""
    setup_logging()
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()