"""
Core game logic
"""

import time
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..models.types import ChatID, GameMode, Question, MessageID
from ..models.game_state import get_game_state
from ..utils.error_handler import safe_async_call, log_error, OpenAIError
from ..utils.formatters import format_round_results_team
import questions


@safe_async_call("start_round")
async def start_round(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Start a new round of the game"""
    game_state = get_game_state(chat_id)
    
    if not game_state.settings:
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка: настройки игры не заданы. Используйте /start для настройки."
        )
        return
    
    settings = game_state.settings
    
    # Generate questions for the round
    await context.bot.send_message(chat_id, "🧠 Генерирую вопросы...")
    
    try:
        # Generate questions using OpenAI
        questions_data = await questions.openai_generate_questions(
            theme=settings.theme,
            round_num=game_state.current_round,
            chat_id=chat_id,
            get_difficulty=lambda cid: settings.difficulty.value,
            get_questions_per_round=lambda cid: settings.questions_per_round
        )
        
        # Convert to Question objects
        question_objects = []
        for q_data in questions_data:
            try:
                question = Question.from_dict(q_data)
                question_objects.append(question)
            except Exception as e:
                log_error(e, f"parsing question: {q_data}", chat_id)
                continue
        
        if not question_objects:
            await context.bot.send_message(
                chat_id, 
                "❌ Ошибка генерации вопросов. Попробуйте позже или измените тему."
            )
            return
        
        game_state.questions = question_objects
        game_state.question_index = 0
        
        # Start asking questions directly (no captain selection needed)
        await ask_next_question(context, chat_id)
            
    except Exception as e:
        log_error(e, "start_round", chat_id)
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка при запуске раунда. Попробуйте позже."
        )


@safe_async_call("ask_next_question")
async def ask_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Ask the next question in the round"""
    game_state = get_game_state(chat_id)
    
    # Clean up service messages
    for msg_id in game_state.service_messages:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    game_state.service_messages.clear()
    
    # Check if round is finished
    if game_state.question_index >= len(game_state.questions):
        await finish_round(context, chat_id)
        return
    
    current_question = game_state.questions[game_state.question_index]
    settings = game_state.settings
    
    if not settings:
        await context.bot.send_message(chat_id, "❌ Ошибка: настройки не найдены.")
        return
    
    # Create question message without buttons - answers via reply
    question_text = (
        f'❓ Вопрос {game_state.question_index + 1}:\n\n'
        f'{current_question.question}\n\n'
        f'⏰ Время: {settings.time_per_question} сек\n'
        f'💬 Ответьте на это сообщение для отправки ответа'
    )
    
    try:
        msg = await context.bot.send_message(chat_id, question_text)
        
        # Store message ID for reply detection
        game_state.service_messages.append(MessageID(msg.message_id))
        game_state.start_question(current_question)
        # Store question message ID for reply detection
        game_state.current_question_message_id = msg.message_id
        
        # Schedule timeout
        context.job_queue.run_once(
            question_timeout,
            settings.time_per_question,
            chat_id=chat_id
        )
        
    except Exception as e:
        log_error(e, "ask_next_question", chat_id)
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка при отправке вопроса."
        )


@safe_async_call("question_timeout")
async def question_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle question timeout"""
    chat_id = ChatID(context.job.chat_id)
    game_state = get_game_state(chat_id)
    
    if not game_state.awaiting_answer:
        return  # Question was already answered
    
    game_state.awaiting_answer = False
    current_question = game_state.current_question
    
    if not current_question:
        return
    
    correct_answer = current_question.correct_answer
    
    await context.bot.send_message(
        chat_id,
        f'⏰ Время истекло!\n\n✅ Правильный ответ: {correct_answer}'
    )
    
    # Add empty answer and no score
    game_state.add_answer('')
    game_state.add_score(0)
    
    # Move to next question
    game_state.next_question()
    await ask_next_question(context, chat_id)


@safe_async_call("finish_round")
async def finish_round(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Finish the current round and show results"""
    game_state = get_game_state(chat_id)
    
    if not game_state.questions or not game_state.settings:
        await context.bot.send_message(chat_id, "❌ Ошибка: данные раунда не найдены.")
        return
    
    # Prepare results
    results = []
    correct_count = 0
    
    for i, (answer, question) in enumerate(zip(game_state.answers, game_state.questions)):
        is_correct = answer.lower() == question.correct_answer.lower()
        if is_correct:
            correct_count += 1
        
        results.append({
            'question': question.question,
            'answer': answer,
            'correct': is_correct,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation
        })
    
    # Format results for team mode
    result_text = format_round_results_team(
        results=results,
        correct=correct_count,
        total=len(game_state.questions),
        fast_bonus=game_state.total_fast_bonus,
        fast_time=None,
        total_score=game_state.total_score,
        total_fast_bonus=game_state.total_fast_bonus
    )
    
    # Create buttons for next actions
    keyboard = []
    
    if game_state.current_round < game_state.settings.rounds:
        keyboard.append([InlineKeyboardButton('🔄 Следующий раунд', callback_data='next_round')])
    
    keyboard.extend([
        [InlineKeyboardButton('🏆 Показать рейтинг', callback_data='show_rating')],
        [InlineKeyboardButton('🚪 Выйти', callback_data='leave')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(chat_id, result_text, reply_markup=reply_markup)
    except Exception as e:
        log_error(e, "finish_round", chat_id)
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка при отображении результатов."
        )