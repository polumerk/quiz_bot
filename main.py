"""
Main entry point for Quiz Bot
"""

import asyncio
import logging
import os
import sys
from typing import Optional

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
from src.models.game_state import reset_game_state
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
    app.add_handler(CommandHandler('debug', debug_command))
    
    # UNIFIED SETTINGS HANDLER - MUST BE FIRST to handle unified_ callbacks
    try:
        from src.handlers.callbacks import unified_settings_callback
        
        # Register unified settings handler for all unified_ callbacks
        app.add_handler(CallbackQueryHandler(unified_settings_callback, pattern='^unified_'))
        
        logging.info("✅ Unified settings handler registered FIRST")
    except ImportError as e:
        logging.warning(f"⚠️ Could not import unified handler: {e}. Using fallback mode.")
        # Fallback - bot will work without unified settings
    
    # Callback query handlers (legacy)
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
    
    # Message handlers (order matters - more specific first!)
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


async def setup_webhook(app) -> Optional[str]:
    """Setup webhook for deployment environments with error handling"""
    webhook_url = None
    webhook_path = f"/{config.TELEGRAM_TOKEN}"
    
    # Try to determine webhook URL
    if config.is_replit_environment():
        webhook_url = config.get_replit_webhook_url()
        logging.info(f"Detected Replit environment")
        
        # Debug: log environment variables
        logging.info(f"REPLIT_URL: {os.getenv('REPLIT_URL')}")
        logging.info(f"REPLIT_DEV_DOMAIN: {os.getenv('REPLIT_DEV_DOMAIN')}")
        logging.info(f"REPL_SLUG: {os.getenv('REPL_SLUG')}")
        logging.info(f"REPL_OWNER: {os.getenv('REPL_OWNER')}")
        
    elif config.WEBHOOK_URL:
        webhook_url = config.WEBHOOK_URL
        logging.info(f"Using configured webhook URL")
    
    if webhook_url:
        full_webhook_url = webhook_url + webhook_path
        logging.info(f"Attempting to set webhook: {full_webhook_url}")
        
        try:
            # Set webhook with proper parameters
            response = await app.bot.set_webhook(
                url=full_webhook_url,
                max_connections=40,
                drop_pending_updates=True
            )
            
            if response:
                logging.info("✅ Webhook set successfully")
                return webhook_path
            else:
                logging.warning("⚠️ Webhook setup returned False")
                
        except Exception as e:
            logging.error(f"❌ Webhook setup failed: {e}")
            logging.info("🔄 Will fallback to polling mode")
            
            # Clear any existing webhook
            try:
                await app.bot.delete_webhook()
                logging.info("Cleared existing webhook")
            except Exception:
                pass
    
    logging.info("No webhook configured, will use polling mode")
    return None


async def run_bot() -> None:
    """Main bot runner"""
    logging.info("=== QUIZ BOT STARTING ===")
    logging.info(f"Python version: {sys.version}")
    
    # Debug environment info
    logging.info("Environment debug info:")
    logging.info(f"  Is Replit: {config.is_replit_environment()}")
    logging.info(f"  Replit URL: {config.get_replit_webhook_url()}")
    
    # Initialize database
    logging.info("Initializing database...")
    try:
        db.init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        sys.exit(1)
    
    # Validate Telegram token
    if not config.TELEGRAM_TOKEN:
        logging.error(
            "❌ Telegram Bot Token not found! Please set it in Replit Secrets:\n"
            "1. 🔒 Open Secrets tab in Replit\n"
            "2. ➕ Add new secret: TELEGRAM_TOKEN = your_bot_token\n"
            "3. 🔄 Restart the bot\n\n"
            "Get token from @BotFather in Telegram"
        )
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
        logging.error("Check if TELEGRAM_TOKEN is valid (get it from @BotFather)")
        sys.exit(1)
    
    # Register handlers
    logging.info("Registering handlers...")
    register_handlers(app)
    logging.info("Handlers registered successfully")
    
    # Register bot commands (menu in Telegram)
    logging.info("Registering bot commands...")
    try:
        # Commands as tuples (command, description)
        commands_ru = [
            ("start", "🎮 Начать новую игру или настроить параметры"),
            ("next", "⏭️ Перейти к следующему раунду"),
            ("stat", "📊 Показать статистику игр и игроков"),
            ("lang", "🌍 Сменить язык интерфейса (русский/английский)"),
            ("news", "📰 Новости и обновления бота"),
            ("exit", "👋 Завершить текущую игру"),
            ("stop", "🛑 Остановить игру"),
            ("debug", "🐛 Переключить режим отладки")
        ]
        
        commands_en = [
            ("start", "🎮 Start new game or configure settings"),
            ("next", "⏭️ Go to next round"),
            ("stat", "📊 Show game and player statistics"),
            ("lang", "🌍 Change interface language (Russian/English)"),
            ("news", "📰 Bot news and updates"),
            ("exit", "👋 End current game"),
            ("stop", "🛑 Stop game"),
            ("debug", "🐛 Toggle debug mode")
        ]
        
        # Register commands for Russian users (default)
        await app.bot.set_my_commands(commands_ru)
        logging.info("✅ Bot commands registered for Russian language")
        
        # Register commands for English users
        await app.bot.set_my_commands(commands_en, language_code="en")
        logging.info("✅ Bot commands registered for English language")
        
        # Log registered commands
        current_commands = await app.bot.get_my_commands()
        logging.info(f"📋 Registered {len(current_commands)} bot commands")
        
    except Exception as e:
        logging.warning(f"⚠️ Could not register bot commands: {e}")
        logging.info("Bot will work without command menu")
    
    # Setup and run
    webhook_path = None
    if not config.FORCE_POLLING:
        webhook_path = await setup_webhook(app)
    else:
        logging.info("🔄 FORCE_POLLING enabled - skipping webhook setup")
    
    if webhook_path and not config.FORCE_POLLING:
        # Webhook mode
        logging.info(f"🌐 Starting webhook server on {config.WEBHOOK_LISTEN}:{config.WEBHOOK_PORT}")
        try:
            webhook_url = config.WEBHOOK_URL or config.get_replit_webhook_url()
            await app.run_webhook(
                listen=config.WEBHOOK_LISTEN,
                port=config.WEBHOOK_PORT,
                url_path=webhook_path,
                webhook_url=webhook_url
            )
        except Exception as e:
            logging.error(f"❌ Webhook server failed: {e}")
            logging.info("🔄 Attempting fallback to polling mode...")
            
            # Clear webhook and create fresh app for polling
            try:
                await app.bot.delete_webhook()
                logging.info("Cleared webhook, creating fresh app for polling...")
                
                # Create a new application instance for polling to avoid state issues
                polling_app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
                register_handlers(polling_app)
                
                logging.info("📡 Starting polling with fresh application...")
                await polling_app.run_polling(drop_pending_updates=True)
                
            except Exception as polling_error:
                logging.error(f"❌ Polling fallback also failed: {polling_error}")
                
                # Last resort: Try simple polling without complex setup
                logging.info("🆘 Trying basic polling as last resort...")
                try:
                    basic_app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
                    register_handlers(basic_app) 
                    await basic_app.run_polling(drop_pending_updates=True)
                except Exception as final_error:
                    logging.error(f"❌ All methods failed: {final_error}")
                    return  # Exit gracefully instead of raising
    else:
        # Polling mode
        logging.info("📡 Starting polling mode...")
        
        # Force clear any existing webhook
        try:
            await app.bot.delete_webhook(drop_pending_updates=True)
            logging.info("✅ Webhook cleared for polling mode")
        except Exception as e:
            logging.warning(f"Could not clear webhook: {e}")
        
        try:
            await app.run_polling(drop_pending_updates=True)
        except RuntimeError as e:
            if "already running" in str(e) or "Cannot close a running event loop" in str(e):
                logging.error("Event loop conflict. Cannot run in this environment.")
                sys.exit(1)
            else:
                raise
        except Exception as e:
            logging.error(f"❌ Polling failed: {e}")
            raise
    
    logging.info("Bot stopped")


def main() -> None:
    """Entry point with event loop handling for different environments"""
    setup_logging()
    
    try:
        # Try nest_asyncio approach first (best for Replit)
        try:
            # This will work if nest_asyncio is applied
            asyncio.run(run_bot())
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                logging.info("🔄 Detected running event loop, trying alternative approach...")
                
                # Try to get existing loop and run there
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in a running loop (like Replit), create a task
                        logging.info("📋 Creating task in existing loop")
                        task = loop.create_task(run_bot())
                        # In Replit this should work with nest_asyncio
                        loop.run_until_complete(task)
                    else:
                        # Loop exists but not running
                        logging.info("🚀 Running in existing non-running loop")
                        loop.run_until_complete(run_bot())
                except Exception as loop_error:
                    logging.error(f"❌ Loop handling failed: {loop_error}")
                    raise
            else:
                # Some other runtime error
                raise
            
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        if "Cannot close a running event loop" in str(e):
            logging.info("Event loop handled gracefully")
        else:
            logging.error(f"Fatal error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()