"""
Message handlers for Telegram bot
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..models.types import ChatID, UserID
from ..models.game_state import get_game_state
from ..utils.error_handler import safe_async_call, log_error
# from .callbacks import _send_registration_message  # Not needed anymore
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
    
    # Clean up theme-related messages for clean chat
    from ..utils.error_handler import safe_delete_message
    try:
        # Delete the theme request message (bot's message asking for theme)
        # Delete the user's reply with theme
        await update.message.delete()
        # Try to delete some recent service messages
        for msg_id in game_state.service_messages[-2:]:  # Last 2 messages
            await safe_delete_message(context, chat_id, msg_id)
    except Exception:
        pass  # Ignore deletion errors
    
    # Edit the existing settings message instead of creating new one
    try:
        if game_state.settings_message_id:
            from .callbacks import _edit_unified_settings_message
            await _edit_unified_settings_message(context, chat_id, game_state.settings_message_id)
        else:
            # Fallback to creating new settings menu if no saved message ID
            from .commands import _send_unified_settings
            await _send_unified_settings(context, chat_id)
    except Exception:
        # Fallback - send success message
        await context.bot.send_message(
            chat_id, 
            f'✅ Тема установлена: {theme}\nИспользуйте /start для настройки игры.'
        )


@safe_async_call("answer_message_handler")
async def answer_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle answer text message via reply to question"""
    if not update.message or not update.message.chat:
        return
        
    chat_id = ChatID(update.message.chat.id)
    game_state = get_game_state(chat_id)
    
    # Check if this is a reply to current question
    if not (update.message.reply_to_message and 
            game_state.current_question and 
            game_state.current_question_message_id and
            update.message.reply_to_message.message_id == game_state.current_question_message_id):
        return
    
    # Check if we're waiting for answers
    if not game_state.awaiting_answer:
        return
    
    # Debug logging
    from ..config import config
    if config.DEBUG_MODE:
        import logging
        logging.info(f"🐛 DEBUG: Answer received for question ID: {game_state.current_question_id}, index: {game_state.question_index}")
    
    game_state.awaiting_answer = False
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
        f'{status} Ваш ответ: {user_answer}{bonus_text}{time_text}'
    )
    
    # Move to next question
    game_state.next_question()
    
    # Import here to avoid circular imports
    from ..game.logic import ask_next_question
    await ask_next_question(context, chat_id)


@safe_async_call("lang_choice_handler")
async def lang_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language choice message (only when expecting language selection)"""
    if not update.message or not update.message.chat:
        return
        
    chat_id = ChatID(update.message.chat.id)
    game_state = get_game_state(chat_id)
    
    # Only process if we're waiting for language selection
    if not game_state.awaiting_language:
        return
    
    text = update.message.text.lower() if update.message.text else ''
    
    # Reset the awaiting flag
    game_state.awaiting_language = False
    
    # Import here to avoid circular imports
    from telegram import ReplyKeyboardRemove
    
    if "рус" in text:
        lang.set_language(chat_id, "ru")
        await update.message.reply_text(
            "Язык переключён на русский 🇷🇺", 
            reply_markup=ReplyKeyboardRemove()
        )
    elif "eng" in text:
        lang.set_language(chat_id, "en")
        await update.message.reply_text(
            "Language switched to English 🇬🇧", 
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Неизвестный язык / Unknown language", 
            reply_markup=ReplyKeyboardRemove()
        )