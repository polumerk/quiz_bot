"""
Message handlers for Telegram bot
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..models.types import ChatID, UserID
from ..models.game_state import get_game_state
from ..utils.error_handler import safe_async_call, log_error
from .callbacks import _send_registration_message
import lang


@safe_async_call("theme_message_handler")
async def theme_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme input message"""
    if not update.message or not update.message.chat:
        return
        
    chat_id = ChatID(update.message.chat.id)
    game_state = get_game_state(chat_id)
    
    if not game_state.awaiting_theme:
        return
    
    theme = update.message.text.strip()
    
    if len(theme) < 2:
        await update.message.reply_text('Тема должна содержать минимум 2 символа.')
        return
    
    # Set theme in settings
    if game_state.settings:
        game_state.settings.theme = theme
    
    game_state.awaiting_theme = False
    
    await _send_registration_message(context, chat_id)


@safe_async_call("answer_message_handler")
async def answer_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle answer text message"""
    if not update.message or not update.message.chat:
        return
        
    chat_id = ChatID(update.message.chat.id)
    game_state = get_game_state(chat_id)
    
    if not game_state.awaiting_text_answer:
        return
    
    game_state.awaiting_text_answer = False
    user_answer = update.message.text.strip()
    
    if not game_state.current_question:
        await update.message.reply_text("Ошибка: нет активного вопроса.")
        return
    
    correct_answer = game_state.current_question.correct_answer
    question_text = game_state.current_question.question
    
    # Check if answer is correct
    is_correct = user_answer.lower() == correct_answer.lower()
    
    # Check for fast bonus
    answer_time = game_state.calculate_answer_time()
    fast_bonus = 0
    
    if is_correct and game_state.is_fast_answer():
        fast_bonus = 1
        game_state.add_fast_bonus(1)
    
    # Add results
    game_state.add_answer(user_answer)
    game_state.add_score(1 if is_correct else 0)
    
    # Format response
    status = '✅' if is_correct else '❌'
    bonus_text = f' ⚡ Бонус за быстрый ответ!' if fast_bonus else ''
    time_text = f' (за {int(answer_time)} сек)' if fast_bonus else ''
    
    await update.message.reply_text(
        f'{status} Ваш ответ: {user_answer}\n'
        f'Правильный ответ: {correct_answer}\n'
        f'{bonus_text}{time_text}'
    )
    
    # Move to next question
    game_state.next_question()
    
    # Import here to avoid circular imports
    from ..game.logic import ask_next_question
    await ask_next_question(context, chat_id)


@safe_async_call("lang_choice_handler")
async def lang_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language choice message"""
    if not update.message or not update.message.chat:
        return
        
    chat_id = ChatID(update.message.chat.id)
    text = update.message.text.lower() if update.message.text else ''
    
    if "рус" in text:
        lang.set_language(chat_id, "ru")
        await update.message.reply_text("Язык переключён на русский 🇷🇺")
    elif "eng" in text:
        lang.set_language(chat_id, "en")
        await update.message.reply_text("Language switched to English 🇬🇧")
    else:
        await update.message.reply_text("Неизвестный язык / Unknown language")