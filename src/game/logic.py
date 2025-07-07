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
        
        import logging
        logging.info(f"DEBUG: OpenAI returned {len(questions_data)} questions: {questions_data}")
        
        # Check if OpenAI returned error
        if (len(questions_data) == 1 and 
            isinstance(questions_data[0], dict) and 
            "Ошибка генерации вопросов" in str(questions_data[0].get('question', ''))):
            await context.bot.send_message(
                chat_id, 
                "❌ Ошибка генерации вопросов через OpenAI. Проверьте:\n"
                "• Корректность API ключа\n"
                "• Доступность OpenAI API\n"
                "• Тему (попробуйте другую)\n\n"
                "Попробуйте позже или измените настройки."
            )
            return
        
        # Convert to Question objects
        question_objects = []
        for i, q_data in enumerate(questions_data):
            try:
                logging.info(f"DEBUG: Processing question {i}: {q_data}")
                
                # Validate question data
                if not isinstance(q_data, dict):
                    logging.error(f"Question {i} is not a dict: {q_data}")
                    continue
                
                required_fields = ['question']
                if not all(field in q_data for field in required_fields):
                    logging.error(f"Question {i} missing required fields: {q_data}")
                    continue
                
                question = Question.from_dict(q_data)
                question_objects.append(question)
                logging.info(f"DEBUG: Successfully parsed question {i}: {question.question}")
                
            except Exception as e:
                log_error(e, f"parsing question {i}: {q_data}", chat_id)
                continue
        
        if not question_objects:
            await context.bot.send_message(
                chat_id, 
                "❌ Не удалось создать вопросы из ответа OpenAI.\n"
                "Попробуйте изменить тему или проверьте настройки API."
            )
            return
        
        logging.info(f"DEBUG: Successfully created {len(question_objects)} Question objects")
        
        game_state.questions = question_objects
        game_state.question_index = 0
        
        # Start asking questions directly (no captain selection needed)
        await ask_next_question(context, chat_id)
            
    except Exception as e:
        log_error(e, "start_round", chat_id)
        await context.bot.send_message(
            chat_id, 
            f"❌ Ошибка при запуске раунда: {str(e)}\n"
            "Попробуйте позже или проверьте настройки."
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
        
        # Schedule timeout (only if job_queue is available)
        if context.job_queue:
            context.job_queue.run_once(
                question_timeout,
                settings.time_per_question,
                chat_id=chat_id
            )
        else:
            # Fallback: no timeout, users can answer anytime
            import logging
            logging.warning(f"JobQueue not available - no question timeout (Chat ID: {chat_id})")
        
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