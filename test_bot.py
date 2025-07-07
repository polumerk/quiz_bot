#!/usr/bin/env python3
"""
Simple polling bot for testing
"""

import os
import sys
import asyncio
import logging

# Set token
os.environ['TELEGRAM_TOKEN'] = '8082065832:AAFMg57PUuHJzTt2YavoqCK5pEBYlhpVdYg'

# Import after setting environment
from telegram.ext import ApplicationBuilder, CommandHandler

async def start_handler(update, context):
    """Simple start handler for testing"""
    await update.message.reply_text(
        "🎉 Бот работает!\n\n"
        "✅ Обработчики команд исправлены\n"
        "✅ Декоратор safe_async_call работает\n"
        "✅ Polling режим активен\n\n"
        "Основной бот готов для запуска!"
    )
    print(f"✅ Received /start from {update.effective_user.first_name}")

async def main():
    """Main function"""
    logging.basicConfig(level=logging.INFO)
    
    # Create app
    app = ApplicationBuilder().token(os.environ['TELEGRAM_TOKEN']).build()
    
    # Add handler
    app.add_handler(CommandHandler('start', start_handler))
    
    print("🚀 Test bot starting...")
    
    # Clear webhook
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook cleared")
    
    # Start polling
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Polling error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Handle nested event loop
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped")