"""
Callback query handlers for Telegram bot
"""

from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..models.types import ChatID, GameMode, Difficulty, UserID
from ..models.game_state import get_game_state, reset_game_state
from ..utils.error_handler import safe_async_call, log_error
from ..utils.formatters import format_round_results_team
from .commands import _send_settings_message


__all__ = [
    'mode_callback', 'difficulty_callback', 'rounds_callback', 
    'questions_callback', 'time_callback', 'join_callback',
    'end_registration_callback', 'captain_callback', 'answer_callback',
    'next_round_callback', 'show_rating_callback', 'leave_callback',
    'change_mode_callback', 'change_difficulty_callback', 'change_rounds_callback',
    'change_questions_callback', 'change_time_callback', 'change_theme_callback',
    'start_game_callback', 'back_to_settings_callback', 'set_mode_callback',
    'set_difficulty_callback', 'set_rounds_callback', 'set_questions_callback',
    'set_time_callback'
]


@safe_async_call("change_mode_callback")
async def change_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change mode button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    keyboard = [
        [InlineKeyboardButton('Командный', callback_data='set_mode_team')],
        [InlineKeyboardButton('Индивидуальный', callback_data='set_mode_individual')],
        [InlineKeyboardButton('◀️ Назад', callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="🎮 Выберите режим игры:",
        reply_markup=reply_markup
    )


@safe_async_call("change_difficulty_callback")
async def change_difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change difficulty button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    keyboard = [
        [InlineKeyboardButton('Легкий', callback_data='set_difficulty_easy')],
        [InlineKeyboardButton('Средний', callback_data='set_difficulty_medium')],
        [InlineKeyboardButton('Сложный', callback_data='set_difficulty_hard')],
        [InlineKeyboardButton('◀️ Назад', callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="🎯 Выберите уровень сложности:",
        reply_markup=reply_markup
    )


@safe_async_call("change_rounds_callback")
async def change_rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change rounds button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    keyboard = [
        [InlineKeyboardButton(str(r), callback_data=f'set_rounds_{r}') for r in range(1, 4)],
        [InlineKeyboardButton(str(r), callback_data=f'set_rounds_{r}') for r in range(4, 7)],
        [InlineKeyboardButton('◀️ Назад', callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="🔄 Выберите количество раундов:",
        reply_markup=reply_markup
    )


@safe_async_call("change_questions_callback")
async def change_questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change questions button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    keyboard = [
        [InlineKeyboardButton(str(q), callback_data=f'set_questions_{q}') for q in range(3, 6)],
        [InlineKeyboardButton(str(q), callback_data=f'set_questions_{q}') for q in range(6, 9)],
        [InlineKeyboardButton(str(q), callback_data=f'set_questions_{q}') for q in range(9, 12)],
        [InlineKeyboardButton('◀️ Назад', callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="❓ Выберите количество вопросов в раунде:",
        reply_markup=reply_markup
    )


@safe_async_call("change_time_callback")
async def change_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change time button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    keyboard = [
        [InlineKeyboardButton('30 сек', callback_data='set_time_30')],
        [InlineKeyboardButton('60 сек', callback_data='set_time_60')],
        [InlineKeyboardButton('120 сек', callback_data='set_time_120')],
        [InlineKeyboardButton('300 сек', callback_data='set_time_300')],
        [InlineKeyboardButton('◀️ Назад', callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="⏰ Выберите время на вопрос:",
        reply_markup=reply_markup
    )


@safe_async_call("change_theme_callback")
async def change_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle change theme button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    game_state.awaiting_theme = True
    
    await context.bot.send_message(
        chat_id, 
        '📚 Введите тему для вопросов (например: "история", "наука", "спорт"):'
    )


@safe_async_call("start_game_callback")
async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start game button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    if not game_state.settings or not game_state.settings.theme:
        await context.bot.send_message(
            chat_id, 
            '❌ Пожалуйста, сначала задайте тему для вопросов.'
        )
        return
    
    await _send_registration_message(context, chat_id)


@safe_async_call("back_to_settings_callback")
async def back_to_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back to settings button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


# Set callbacks for the unified settings
@safe_async_call("set_mode_callback")
async def set_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle set mode callback"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    mode_str = query.data.split('_')[2]
    mode = GameMode.TEAM if mode_str == 'team' else GameMode.INDIVIDUAL
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=mode,
            difficulty=Difficulty.MEDIUM,
            rounds=2,
            questions_per_round=5,
            time_per_question=300,
            theme=""
        )
    else:
        game_state.settings.mode = mode
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


@safe_async_call("set_difficulty_callback")
async def set_difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle set difficulty callback"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    difficulty_str = query.data.split('_')[2]
    difficulty = Difficulty(difficulty_str)
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=GameMode.TEAM,
            difficulty=difficulty,
            rounds=2,
            questions_per_round=5,
            time_per_question=300,
            theme=""
        )
    else:
        game_state.settings.difficulty = difficulty
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


@safe_async_call("set_rounds_callback")
async def set_rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle set rounds callback"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    rounds = int(query.data.split('_')[2])
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=GameMode.TEAM,
            difficulty=Difficulty.MEDIUM,
            rounds=rounds,
            questions_per_round=5,
            time_per_question=300,
            theme=""
        )
    else:
        game_state.settings.rounds = rounds
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


@safe_async_call("set_questions_callback")
async def set_questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle set questions callback"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    questions_count = int(query.data.split('_')[2])
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=GameMode.TEAM,
            difficulty=Difficulty.MEDIUM,
            rounds=2,
            questions_per_round=questions_count,
            time_per_question=300,
            theme=""
        )
    else:
        game_state.settings.questions_per_round = questions_count
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


@safe_async_call("set_time_callback")
async def set_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle set time callback"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    time_per_question = int(query.data.split('_')[2])
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=GameMode.TEAM,
            difficulty=Difficulty.MEDIUM,
            rounds=2,
            questions_per_round=5,
            time_per_question=time_per_question,
            theme=""
        )
    else:
        game_state.settings.time_per_question = time_per_question
    
    from .commands import _send_unified_settings
    await _send_unified_settings(context, chat_id)


@safe_async_call("mode_callback")
async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle game mode selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    mode_str = query.data.split('_')[1]
    mode = GameMode.TEAM if mode_str == 'team' else GameMode.INDIVIDUAL
    
    if not game_state.settings:
        from ..models.types import GameSettings
        game_state.settings = GameSettings(
            mode=mode,
            difficulty=Difficulty.MEDIUM,
            rounds=2,
            questions_per_round=2,
            time_per_question=300,
            theme=""
        )
    else:
        game_state.settings.mode = mode
    
    await _send_settings_message(context, chat_id, 'difficulty')


@safe_async_call("difficulty_callback")
async def difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle difficulty selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    difficulty_str = query.data.split('_')[1]
    difficulty = Difficulty(difficulty_str)
    
    if game_state.settings:
        game_state.settings.difficulty = difficulty
    
    await _send_settings_message(context, chat_id, 'rounds')


@safe_async_call("rounds_callback")
async def rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rounds count selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    rounds = int(query.data.split('_')[1])
    
    if game_state.settings:
        game_state.settings.rounds = rounds
    
    await _send_settings_message(context, chat_id, 'questions')


@safe_async_call("questions_callback")
async def questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle questions per round selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    questions_count = int(query.data.split('_')[1])
    
    if game_state.settings:
        game_state.settings.questions_per_round = questions_count
    
    await _send_settings_message(context, chat_id, 'time')


@safe_async_call("time_callback")
async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle time per question selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    time_per_question = int(query.data.split('_')[1])
    
    if game_state.settings:
        game_state.settings.time_per_question = time_per_question
    
    # Set flag to await theme input
    game_state.awaiting_theme = True
    
    await _send_settings_message(context, chat_id, 'theme')


@safe_async_call("join_callback")
async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle participant joining"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    user_id = UserID(query.from_user.id)
    username = query.from_user.first_name or query.from_user.username or 'Неизвестный'
    
    game_state = get_game_state(chat_id)
    game_state.add_participant(user_id, username)
    
    await _send_registration_message(context, chat_id)


@safe_async_call("end_registration_callback")
async def end_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle end registration"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    await _end_registration(context, chat_id)


@safe_async_call("captain_callback")
async def captain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle captain selection"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    captain_id = UserID(int(query.data.split('_')[1]))
    
    game_state = get_game_state(chat_id)
    game_state.set_captain(captain_id)
    
    # Import here to avoid circular imports
    from ..game.logic import ask_next_question
    await ask_next_question(context, chat_id)


@safe_async_call("answer_callback")
async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle answer button press - NO LONGER USED (keeping for compatibility)"""
    if not update.callback_query:
        return
    await update.callback_query.answer("Ответы теперь принимаются как reply на вопрос!")


@safe_async_call("next_round_callback")
async def next_round_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle next round button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    game_state.next_round()
    
    # Import here to avoid circular imports
    from ..game.logic import start_round
    await start_round(context, chat_id)


@safe_async_call("show_rating_callback")
async def show_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle show rating button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    game_state = get_game_state(chat_id)
    
    total_points = game_state.get_total_points()
    
    text = f'🏆 Итоговый рейтинг:\n\n'
    text += f'✅ Правильных ответов: {game_state.total_score}\n'
    text += f'⚡ Бонусов за скорость: {game_state.total_fast_bonus}\n'
    text += f'⭐ Общий счёт: {total_points} баллов'
    
    keyboard = [[InlineKeyboardButton('🚪 Выйти', callback_data='leave')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id, text, reply_markup=reply_markup)


@safe_async_call("leave_callback")
async def leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leave game button"""
    if not update.callback_query or not update.callback_query.message:
        return
        
    query = update.callback_query
    await query.answer()
    
    chat_id = ChatID(query.message.chat.id)
    reset_game_state(chat_id)
    
    await context.bot.send_message(
        chat_id, 
        '👋 Игра завершена! Используйте /start для новой игры.'
    )


async def _send_registration_message(
    context: ContextTypes.DEFAULT_TYPE, 
    chat_id: ChatID, 
    countdown: Optional[int] = None
) -> None:
    """Send registration message with participant list"""
    game_state = get_game_state(chat_id)
    participants = game_state.participants
    
    keyboard = [
        [InlineKeyboardButton('🎯 Присоединиться', callback_data='join')],
        [InlineKeyboardButton('✅ Завершить регистрацию', callback_data='end_registration')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f'🎮 Регистрация участников\n\nУчастники ({len(participants)}):\n'
    for participant in participants:
        text += f'• {participant.username}\n'
    
    if countdown:
        text += f'\n⏰ Осталось: {countdown} сек'
    
    await context.bot.send_message(chat_id, text, reply_markup=reply_markup)


async def _end_registration(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """End registration and start game"""
    game_state = get_game_state(chat_id)
    participants = game_state.participants
    
    if len(participants) < 1:
        await context.bot.send_message(
            chat_id, 
            '❌ Нужен минимум 1 участник для начала игры.'
        )
        return
    
    # Import here to avoid circular imports
    from ..game.logic import start_round
    await start_round(context, chat_id)