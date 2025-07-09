"""
Message handlers for Telegram bot
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..models.types import ChatID, UserID, GameMode
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
    if not update.message or not update.message.chat or not update.message.from_user:
        return
        
    chat_id = ChatID(update.message.chat.id)
    user_id = UserID(update.message.from_user.id)
    username = update.message.from_user.first_name or "Unknown"
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
    
    # Check if user is a registered participant
    participant = game_state.get_participant(user_id)
    if not participant:
        await update.message.reply_text("❌ Вы не зарегистрированы для участия в игре!")
        return
    
    # Check if user already answered this question
    if game_state.has_user_answered(user_id):
        await update.message.reply_text("❌ Вы уже ответили на этот вопрос!")
        return
    
    # In team mode, only captain can answer
    if (game_state.settings and 
        game_state.settings.mode == GameMode.TEAM and 
        game_state.captain_id and 
        user_id != game_state.captain_id):
        captain_participant = game_state.get_participant(game_state.captain_id)
        captain_name = captain_participant.username if captain_participant else "Капитан"
        await update.message.reply_text(f"❌ В командном режиме отвечает только капитан ({captain_name})!")
        return
    
    # Debug logging
    from ..config import config
    if config.DEBUG_MODE:
        import logging
        logging.info(f"🐛 DEBUG: Answer received from {username} for question ID: {game_state.current_question_id}, index: {game_state.question_index}")
    
    user_answer = update.message.text.strip()
    
    if not game_state.current_question:
        await update.message.reply_text("Ошибка: нет активного вопроса.")
        return
    
    correct_answer = game_state.current_question.correct_answer
    
    # Check if answer is correct
    is_correct = user_answer.lower() == correct_answer.lower()
    
    # Add user's answer to game state
    game_state.add_user_answer(user_id, username, user_answer, is_correct)
    
    # Get the stored answer for bonus info
    stored_answer = game_state.current_question_answers[user_id]
    
    # Update global scoring
    if is_correct:
        game_state.add_score(1)
        if stored_answer.fast_bonus:
            game_state.add_fast_bonus(1)
    
    # Add to answers list for compatibility
    game_state.add_answer(user_answer)
    
    # Confirm answer received without revealing correctness
    # Different message for team vs individual mode
    # Send confirmation with reply to user's answer message
    if game_state.settings and game_state.settings.mode == GameMode.TEAM:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f'📝 Ваш ответ принят: {user_answer}\n'
                 f'⏳ Переходим к следующему вопросу...',
            reply_to_message_id=update.message.message_id
        )
    else:
        unanswered_count = len(game_state.get_unanswered_participants())
        if unanswered_count > 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f'📝 Ваш ответ принят: {user_answer}\n'
                     f'⏳ Ожидаю ответов от {unanswered_count} участников...',
                reply_to_message_id=update.message.message_id
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f'📝 Ваш ответ принят: {user_answer}\n'
                     f'⏳ Переходим к следующему вопросу...',
                reply_to_message_id=update.message.message_id
            )
    
    # Check if we should wait for more answers
    if game_state.should_wait_for_more_answers():
        # Still waiting for more participants
        unanswered = game_state.get_unanswered_participants()
        if config.DEBUG_MODE:
            unanswered_names = [p.username for p in unanswered]
            logging.info(f"🐛 DEBUG: Still waiting for answers from: {unanswered_names}")
        return
    
    # All participants answered (or it's team mode and captain answered)
    game_state.awaiting_answer = False
    
    if config.DEBUG_MODE:
        logging.info(f"🐛 DEBUG: All participants answered, moving to next question")
    
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
    
    if "рус" in text:
        lang.set_language(chat_id, "ru")
        await update.message.reply_text("Язык переключён на русский 🇷🇺")
    elif "eng" in text:
        lang.set_language(chat_id, "en")
        await update.message.reply_text("Language switched to English 🇬🇧")
    else:
        await update.message.reply_text("Неизвестный язык / Unknown language")