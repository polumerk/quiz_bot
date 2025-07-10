"""
Core game logic
"""

import time
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..models.types import ChatID, GameMode, Question, MessageID, UserID
from ..models.game_state import get_game_state
from ..utils.error_handler import safe_async_call, log_error, OpenAIError
from ..utils.formatters import format_round_results_team, format_round_results_individual
from ..utils.integration_helper import integration_helper
from ..config import config
import questions
import asyncio


async def preload_next_question(game_state, chat_id):
    """Асинхронно генерирует следующий вопрос и сохраняет его в preloaded_question"""
    if game_state.is_generating_question:
        return
    game_state.is_generating_question = True
    try:
        from src.utils.question_types import get_random_question_type
        settings = game_state.settings
        if not settings:
            return
        question_type = get_random_question_type(settings.theme)
        question_data = await integration_helper.generate_enhanced_questions(
            theme=settings.theme,
            round_num=game_state.current_round,
            chat_id=chat_id,
            get_difficulty=lambda cid: settings.difficulty.value,
            get_questions_per_round=lambda cid: 1
        )
        if question_data and isinstance(question_data, list) and question_data[0].get('question'):
            question = Question.from_dict(question_data[0])
            game_state.preloaded_question = question
    except Exception as e:
        from ..utils.error_handler import log_error
        log_error(e, "preload_next_question", chat_id)
    finally:
        game_state.is_generating_question = False


@safe_async_call("start_round")
async def start_round(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Start a new round of the game (ленивая генерация вопросов)"""
    game_state = get_game_state(chat_id)
    
    if not game_state.settings:
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка: настройки игры не заданы. Используйте /start для настройки."
        )
        return
    
    settings = game_state.settings
    game_state.question_index = 0
    game_state.current_question = None
    game_state.question_history.clear()
    await context.bot.send_message(chat_id, "🧠 Генерирую первый вопрос...")
    await ask_next_question(context, chat_id)


@safe_async_call("ask_next_question")
async def ask_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Ленивая генерация и показ следующего вопроса с preloading"""
    game_state = get_game_state(chat_id)
    settings = game_state.settings
    if not settings:
        await context.bot.send_message(chat_id, "❌ Ошибка: настройки не найдены.")
        return
    # Проверяем, не идёт ли уже генерация
    if game_state.is_generating_question:
        await context.bot.send_message(chat_id, "⏳ Вопрос уже генерируется, подождите...")
        return
    # Используем preloaded_question, если он есть
    if game_state.preloaded_question:
        question = game_state.preloaded_question
        game_state.preloaded_question = None
    else:
        # Генерируем вопрос синхронно, если preload не сработал
        from src.utils.question_types import get_random_question_type
        question_type = get_random_question_type(settings.theme)
        question_data = await integration_helper.generate_enhanced_questions(
            theme=settings.theme,
            round_num=game_state.current_round,
            chat_id=chat_id,
            get_difficulty=lambda cid: settings.difficulty.value,
            get_questions_per_round=lambda cid: 1
        )
        if not question_data or not isinstance(question_data, list) or not question_data[0].get('question'):
            await context.bot.send_message(chat_id, "❌ Не удалось сгенерировать вопрос. Попробуйте позже.")
            return
        question = Question.from_dict(question_data[0])
    game_state.current_question = question
    game_state.question_history[game_state.question_index] = question
    # Формируем текст вопроса
    left_part = f'❓ Вопрос {game_state.question_index + 1}'
    right_part = f'⏰ {settings.time_per_question} сек'
    total_width = 40
    padding_needed = total_width - len(left_part) - len(right_part)
    padding = ' ' * max(1, padding_needed)
    question_text = (
        f'`{left_part}{padding}{right_part}`\n\n'
        f'{question.question}\n\n'
        f'💬 Как ответить: reply на это сообщение'
    )
    msg = await context.bot.send_message(chat_id, question_text)
    game_state.service_messages.append(MessageID(msg.message_id))
    question_id = game_state.start_question(question)
    game_state.current_question_message_id = MessageID(msg.message_id)
    # Таймер
    if context.job_queue:
        context.job_queue.run_once(
            question_timeout,
            settings.time_per_question,
            chat_id=chat_id,
            data={'question_id': question_id, 'question_index': game_state.question_index}
        )
    # После показа вопроса — preload следующего
    asyncio.create_task(preload_next_question(game_state, chat_id))


@safe_async_call("question_timeout")
async def question_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle question timeout with question ID validation"""
    if not context.job:
        return
    
    chat_id = ChatID(context.job.chat_id)
    game_state = get_game_state(chat_id)
    
    # Get timeout data safely
    timeout_question_id = None
    timeout_question_index = None
    if hasattr(context.job, 'data') and context.job.data:
        try:
            timeout_question_id = context.job.data.get('question_id')  # type: ignore
            timeout_question_index = context.job.data.get('question_index')  # type: ignore
        except (AttributeError, TypeError):
            pass
    
    # Debug logging
    if config.DEBUG_MODE:
        import logging
        logging.info(f"🐛 DEBUG: Timeout triggered for question ID: {timeout_question_id}, index: {timeout_question_index}")
        logging.info(f"🐛 DEBUG: Current question ID: {game_state.current_question_id}, index: {game_state.question_index}")
        logging.info(f"🐛 DEBUG: Awaiting answer: {game_state.awaiting_answer}")
    
    # Check if this timeout is for the current question
    if (timeout_question_id != game_state.current_question_id or 
        timeout_question_index != game_state.question_index):
        if config.DEBUG_MODE:
            import logging
            logging.info(f"🐛 DEBUG: Ignoring timeout for old question (ID mismatch or question changed)")
        return  # This timeout is for an old question
    
    if not game_state.awaiting_answer:
        if config.DEBUG_MODE:
            import logging
            logging.info(f"🐛 DEBUG: Ignoring timeout - not awaiting answer anymore")
        return  # Question was already answered
    
    game_state.awaiting_answer = False
    current_question = game_state.current_question
    
    if not current_question:
        if config.DEBUG_MODE:
            import logging
            logging.info(f"🐛 DEBUG: No current question found")
        return
    
    correct_answer = current_question.correct_answer
    
    if config.DEBUG_MODE:
        import logging
        logging.info(f"🐛 DEBUG: Processing timeout for question: {current_question.question}")
    
    # Add empty answers for participants who didn't respond
    unanswered_participants = game_state.get_unanswered_participants()
    
    if unanswered_participants:
        for participant in unanswered_participants:
            if participant.user_id is None:
                continue
            game_state.add_user_answer(UserID(participant.user_id), participant.username, '', False)
    
    # Notify about timeout and move to next question
    await context.bot.send_message(chat_id, "⏰ Время истекло! Переходим к следующему вопросу...")
    
    # Move to next question
    game_state.next_question()
    await ask_next_question(context, chat_id)


@safe_async_call("finish_round")
async def finish_round(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Finish the current round and show results (ленивая генерация)"""
    game_state = get_game_state(chat_id)
    if not game_state.question_history or not game_state.settings:
        await context.bot.send_message(chat_id, "❌ Ошибка: данные раунда не найдены.")
        return
    # Save the last question's answers if they haven't been saved yet
    if game_state.current_question_answers and game_state.question_index not in game_state.all_question_answers:
        game_state.all_question_answers[game_state.question_index] = game_state.current_question_answers.copy()
    
    def normalize_answer(answer: str) -> str:
        """Normalize answer for comparison"""
        return answer.lower().strip().replace('ё', 'е').replace('й', 'и')
    
    def is_answer_correct(user_answer: str, correct_answer: str) -> bool:
        """Check if answer is correct with improved fuzzy matching"""
        user_norm = normalize_answer(user_answer)
        correct_norm = normalize_answer(correct_answer)
        
        # Exact match
        if user_norm == correct_norm:
            return True
        
        # Both must be at least 3 characters
        if len(user_norm) < 3 or len(correct_norm) < 3:
            return False
        
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        
        # High similarity threshold for very similar words
        if similarity >= 0.85:
            return True
        
        # УЛУЧШЕННАЯ ЛОГИКА: проверка содержания слов
        user_words = user_norm.split()
        correct_words = correct_norm.split()
        
        # Если одно слово содержится в другом полностью
        if user_norm in correct_norm or correct_norm in user_norm:
            return True
        
        # Проверка пересечения слов
        if user_words and correct_words:
            # Если все слова пользователя есть в правильном ответе
            if all(any(user_word in correct_word or correct_word in user_word 
                      for correct_word in correct_words) 
                   for user_word in user_words):
                return True
            
            # Если все слова правильного ответа есть в ответе пользователя
            if all(any(correct_word in user_word or user_word in correct_word 
                      for user_word in user_words) 
                   for correct_word in correct_words):
                return True
        
        # Проверка схожести отдельных слов
        if user_words and correct_words:
            for user_word in user_words:
                for correct_word in correct_words:
                    if len(user_word) >= 3 and len(correct_word) >= 3:
                        word_similarity = SequenceMatcher(None, user_word, correct_word).ratio()
                        if word_similarity >= 0.85:
                            return True
        
        return False
    
    # Prepare results with correct evaluation using stored answers
    results = []
    correct_count = 0
    
    for question_idx, question in game_state.question_history.items():
        # Get stored answers for this question
        question_answers = game_state.all_question_answers.get(question_idx, {})
        
        # Collect all answers for this question
        answers_text = []
        any_correct = False
        
        for user_id, answer_obj in question_answers.items():
            username = answer_obj.username
            user_answer = answer_obj.answer_text
            
            if user_answer:  # Only show non-empty answers
                # Re-evaluate with improved logic
                is_correct = is_answer_correct(user_answer, question.correct_answer)
                if is_correct:
                    any_correct = True
                answers_text.append(f"{username}: {user_answer}")
        
        if any_correct:
            correct_count += 1
        
        # Format combined answers - keep as comma-separated for now
        # The formatter will handle the nice display
        combined_answers = ", ".join(answers_text) if answers_text else "Нет ответов"
        
        results.append({
            'question': question.question,
            'answer': combined_answers,
            'correct': any_correct,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation or "Без комментария",
            'interesting_fact': question.interesting_fact,
            'source_type': question.source_type,
            'difficulty_level': question.difficulty_level,
            'tags': question.tags
        })
    
    # Check game mode and format results accordingly
    if game_state.settings.mode == GameMode.INDIVIDUAL:
        # Prepare data for individual mode formatter
        participants = {UserID(participant.user_id): participant.username for participant in game_state.participants if participant.user_id is not None}
        
        score_by_user = {}
        fast_bonus_by_user = {}
        explanations_by_user = {}
        
        # Calculate individual scores and prepare explanations
        for participant in game_state.participants:
            if participant.user_id is None:
                continue
            user_id = UserID(participant.user_id)
            username = participant.username
            user_correct = 0
            user_fast_bonus = 0
            user_explanations = []
            
            for question_idx, question in game_state.question_history.items():
                question_answers = game_state.all_question_answers.get(question_idx, {})
                user_answer_obj = question_answers.get(user_id)
                
                if user_answer_obj:
                    user_answer = user_answer_obj.answer_text
                    is_correct = is_answer_correct(user_answer, question.correct_answer) if user_answer else False
                    
                    if is_correct:
                        user_correct += 1
                        if user_answer_obj.fast_bonus:
                            user_fast_bonus += 1
                    
                    # Format user's answer nicely with status
                    status_emoji = "✅" if is_correct else "❌"
                    formatted_answer = f"{status_emoji} {user_answer}" if user_answer else "❌ (нет ответа)"
                    
                    user_explanations.append({
                        'question': question.question,
                        'answer': formatted_answer,
                        'correct': is_correct,
                        'correct_answer': question.correct_answer,
                        'explanation': question.explanation or "Без комментария",
                        'interesting_fact': question.interesting_fact,
                        'source_type': question.source_type,
                        'difficulty_level': question.difficulty_level,
                        'tags': question.tags
                    })
                else:
                    # No answer from this user
                    user_explanations.append({
                        'question': question.question,
                        'answer': "❌ (нет ответа)",
                        'correct': False,
                        'correct_answer': question.correct_answer,
                        'explanation': question.explanation or "Без комментария",
                        'interesting_fact': question.interesting_fact,
                        'source_type': question.source_type,
                        'difficulty_level': question.difficulty_level,
                        'tags': question.tags
                    })
            
            score_by_user[user_id] = user_correct
            fast_bonus_by_user[user_id] = user_fast_bonus
            explanations_by_user[user_id] = user_explanations
        
        result_text = format_round_results_individual(
            participants=participants,
            score_by_user=score_by_user,
            fast_bonus_by_user=fast_bonus_by_user,
            explanations_by_user=explanations_by_user,
            chat_id=chat_id
        )
    else:
        # Team mode - use existing logic
        actual_score = game_state.total_score
        actual_fast_bonus = game_state.total_fast_bonus
        
        result_text = format_round_results_team(
            results=results,
            correct=correct_count,
            total=len(game_state.question_history),
            fast_bonus=actual_fast_bonus,
            fast_time=None,
            total_score=actual_score,
            total_fast_bonus=actual_fast_bonus
        )
    
    # Track game results for analytics
    try:
        game_results = {
            'chat_id': chat_id,
            'round': game_state.current_round,
            'theme': game_state.settings.theme,
            'difficulty': game_state.settings.difficulty.value,
            'mode': game_state.settings.mode.value,
            'total_questions': len(game_state.question_history),
            'correct_answers': correct_count,
            'participants_count': len(game_state.participants),
            'fast_bonus_count': actual_fast_bonus if 'actual_fast_bonus' in locals() else 0
        }
        integration_helper.track_game_results(game_results)
    except Exception as e:
        log_error(e, "tracking game results", chat_id)
    
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