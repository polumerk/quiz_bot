#!/usr/bin/env python3
"""
Quick script to register bot commands
"""

import asyncio
import os
from telegram.ext import ApplicationBuilder

# Commands as tuples (command, description)
COMMANDS_RU = [
    ("start", "🎮 Начать новую игру или настроить параметры"),
    ("next", "⏭️ Перейти к следующему раунду"),
    ("stat", "📊 Показать статистику игр и игроков"),
    ("lang", "🌍 Сменить язык интерфейса (русский/английский)"),
    ("news", "📰 Новости и обновления бота"),
    ("exit", "👋 Завершить текущую игру"),
    ("stop", "🛑 Остановить игру"),
    ("debug", "🐛 Переключить режим отладки")
]

COMMANDS_EN = [
    ("start", "🎮 Start new game or configure settings"),
    ("next", "⏭️ Go to next round"),
    ("stat", "📊 Show game and player statistics"),
    ("lang", "🌍 Change interface language (Russian/English)"),
    ("news", "📰 Bot news and updates"),
    ("exit", "👋 End current game"),
    ("stop", "🛑 Stop game"),
    ("debug", "🐛 Toggle debug mode")
]


async def register_commands(token: str):
    """Register bot commands"""
    
    try:
        # Create bot application
        app = ApplicationBuilder().token(token).build()
        
        print("🤖 Connecting to Telegram Bot API...")
        
        # Register commands for Russian users (default)
        await app.bot.set_my_commands(COMMANDS_RU)
        print("✅ Commands registered for default language (Russian)")
        
        # Register commands for English users
        await app.bot.set_my_commands(COMMANDS_EN, language_code="en")
        print("✅ Commands registered for English language")
        
        # Get current commands to verify
        current_commands = await app.bot.get_my_commands()
        
        print(f"\n📋 Registered commands ({len(current_commands)}):")
        for cmd in current_commands:
            if hasattr(cmd, 'command'):
                print(f"  /{cmd.command} - {cmd.description}")
        
        print(f"\n🎉 Successfully registered {len(COMMANDS_RU)} commands!")
        print("Commands will appear in Telegram bot menu within a few minutes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error registering commands: {e}")
        return False


async def show_commands(token: str):
    """Show current commands"""
    
    try:
        app = ApplicationBuilder().token(token).build()
        
        print("🔍 Fetching current bot commands...")
        
        # Get default commands
        commands = await app.bot.get_my_commands()
        print(f"\n📋 Current commands (default/Russian) - {len(commands)}:")
        for cmd in commands:
            if hasattr(cmd, 'command'):
                print(f"  /{cmd.command} - {cmd.description}")
        
        # Get English commands
        commands_en = await app.bot.get_my_commands(language_code="en")
        print(f"\n📋 Current commands (English) - {len(commands_en)}:")
        for cmd in commands_en:
            if hasattr(cmd, 'command'):
                print(f"  /{cmd.command} - {cmd.description}")
            
    except Exception as e:
        print(f"❌ Error fetching commands: {e}")


def main():
    """Main function"""
    print("🤖 Quiz Bot - Quick Commands Registration")
    print("=" * 45)
    
    # Try to get token from environment
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("TELEGRAM_TOKEN not found in environment variables.")
        token = input("Please enter your Telegram Bot Token: ").strip()
        
        if not token:
            print("❌ No token provided. Exiting.")
            return
    
    print("1. Register commands")
    print("2. Show current commands")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nВыберите действие (1-3): ").strip()
            
            if choice == "1":
                print("\n🔧 Registering commands...")
                success = asyncio.run(register_commands(token))
                if success:
                    print("\n✨ Commands registered! Check your bot in Telegram.")
                    break
                    
            elif choice == "2":
                print("\n🔍 Showing current commands...")
                asyncio.run(show_commands(token))
                
            elif choice == "3":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1-3.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 