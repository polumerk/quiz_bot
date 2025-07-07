"""
Command handlers for Telegram bot
"""

import aiosqlite
from typing import Optional, Dict, Any
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from ..models.types import ChatID, GameMode, Difficulty, GameSettings
from ..models.game_state import get_game_state, reset_game_state
from ..utils.error_handler import safe_async_call, log_error
from ..utils.formatters import format_settings_summary
from ..config import config
import lang


@safe_async_call("start_command")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    
    # Send welcome message with mode selection
    await _send_settings_message(context, chat_id, 'mode')


@safe_async_call("next_command")
async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /next command for next round"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    game_state = get_game_state(chat_id)
    
    # Import here to avoid circular imports
    from ..game.logic import start_round
    
    game_state.next_round()
    await start_round(context, chat_id)


@safe_async_call("exit_command")  
async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exit command"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    reset_game_state(chat_id)
    
    await context.bot.send_message(
        chat_id, 
        '👋 Игра завершена! Используйте /start для новой игры.'
    )


@safe_async_call("stop_command")
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    reset_game_state(chat_id)
    
    await context.bot.send_message(
        chat_id, 
        '🛑 Игра остановлена! Используйте /start для новой игры.'
    )


@safe_async_call("news_command")
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /news command"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    
    await context.bot.send_message(
        chat_id, 
        '📰 Новости и обновления бота:\n\n'
        '🚀 Версия 2.0:\n'
        '• Улучшенная архитектура кода\n'
        '• Полная типизация\n'
        '• Лучшая обработка ошибок\n'
        '• Модульная структура\n'
        '• Повышенная стабильность'
    )


@safe_async_call("lang_command")
async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lang command for language selection"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    
    keyboard = [["Русский", "English"]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        one_time_keyboard=True, 
        resize_keyboard=True
    )
    
    await context.bot.send_message(
        chat_id, 
        "Выберите язык / Choose language:", 
        reply_markup=reply_markup
    )


@safe_async_call("stat_command")
async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stat command to show statistics"""
    if not update.effective_chat:
        return
        
    chat_id = ChatID(update.effective_chat.id)
    
    try:
        async with aiosqlite.connect(config.DATABASE_PATH) as conn:
            # Get total games
            async with conn.execute('SELECT COUNT(*) FROM games') as cursor:
                total_games_row = await cursor.fetchone()
                total_games = total_games_row[0] if total_games_row else 0
            
            # Get top winners
            async with conn.execute(
                'SELECT username, wins FROM users ORDER BY wins DESC, total_score DESC LIMIT 5'
            ) as cursor:
                top_wins = await cursor.fetchall()
            
            # Get top scores
            async with conn.execute(
                'SELECT username, total_score FROM users ORDER BY total_score DESC, wins DESC LIMIT 5'
            ) as cursor:
                top_scores = await cursor.fetchall()
            
            # Get top themes
            async with conn.execute(
                'SELECT theme, COUNT(*) as cnt FROM games GROUP BY theme ORDER BY cnt DESC LIMIT 5'
            ) as cursor:
                top_themes = await cursor.fetchall()
        
        # Format statistics
        lang_code = lang.get_language(chat_id)
        text = f'📊 <b>{lang.get_text("stat", lang=lang_code)}</b>\n\n'
        text += f'{lang.get_text("total_games", lang=lang_code)} <b>{total_games}</b>\n\n'
        
        text += '🏆 <b>' + lang.get_text("top_players", lang=lang_code) + '</b>\n'
        for i, (username, wins) in enumerate(top_wins, 1):
            text += f'{i}. {username or "(без имени)"} — {wins} побед\n'
        
        text += '\n💯 <b>' + lang.get_text("top_scores", lang=lang_code) + '</b>\n'
        for i, (username, score) in enumerate(top_scores, 1):
            text += f'{i}. {username or "(без имени)"} — {score} очков\n'
        
        text += '\n📚 <b>' + lang.get_text("top_themes", lang=lang_code) + '</b>\n'
        for i, (theme, cnt) in enumerate(top_themes, 1):
            text += f'{i}. {theme} — {cnt} игр\n'
        
        await context.bot.send_message(chat_id, text, parse_mode='HTML')
        
    except Exception as e:
        log_error(e, "stat_command", chat_id)
        await context.bot.send_message(
            chat_id, 
            "😕 Ошибка при получении статистики. Попробуйте позже."
        )


async def _send_settings_message(
    context: ContextTypes.DEFAULT_TYPE, 
    chat_id: ChatID, 
    stage: str, 
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """Send configuration message for different stages"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if extra is None:
        extra = {}
    
    text = ''
    keyboard = []
    
    if stage == 'mode':
        emoji = lang.get_emoji('emoji_welcome', chat_id)
        text = f'{emoji} Добро пожаловать в квиз!\nВыберите режим игры:'
        keyboard = [
            [InlineKeyboardButton('Командный', callback_data='mode_team')],
            [InlineKeyboardButton('Каждый сам за себя', callback_data='mode_individual')]
        ]
    elif stage == 'difficulty':
        text = 'Выберите уровень сложности:'
        keyboard = [
            [InlineKeyboardButton('Легкий', callback_data='difficulty_easy')],
            [InlineKeyboardButton('Средний', callback_data='difficulty_medium')],
            [InlineKeyboardButton('Сложный', callback_data='difficulty_hard')]
        ]
    elif stage == 'rounds':
        text = 'Выберите количество раундов:'
        keyboard = [[InlineKeyboardButton(str(r), callback_data=f'rounds_{r}')] 
                   for r in range(1, 6)]
    elif stage == 'questions':
        text = 'Выберите количество вопросов в раунде:'
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f'questions_{q}')] 
                   for q in range(3, 11)]
    elif stage == 'time':
        text = 'Выберите время на вопрос (в секундах):'
        keyboard = [
            [InlineKeyboardButton('30 сек', callback_data='time_30')],
            [InlineKeyboardButton('60 сек', callback_data='time_60')],
            [InlineKeyboardButton('120 сек', callback_data='time_120')],
            [InlineKeyboardButton('300 сек', callback_data='time_300')]
        ]
    elif stage == 'theme':
        text = 'Введите тему для вопросов (например: "история", "наука", "спорт"):'
        keyboard = []
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await context.bot.send_message(chat_id, text, reply_markup=reply_markup)