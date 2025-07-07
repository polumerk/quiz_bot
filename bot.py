# --- Импорты ---
import json
import asyncio
import logging
import re
import time
import random
import os
from typing import Any, Dict, List, Set, Tuple, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
import aiohttp
from collections import defaultdict
import sqlite3
from datetime import datetime
import db
import questions
import lang
from lang import LANGUAGES
import aiosqlite

# --- Константы и настройки ---
TOKEN = '8082065832:AAFMg57PUuHJzTt2YavoqCK5pEBYlhpVdYg'
logging.basicConfig(level=logging.INFO)

# --- State ---
game_state: Dict[Any, Any] = {}

def get_participants(chat_id: int) -> Set[Tuple[int, str]]:
    return game_state.setdefault(chat_id, {}).setdefault('participants', set())

def get_captain(chat_id: int) -> Optional[int]:
    return game_state.setdefault(chat_id, {}).get('captain')

def set_captain(chat_id: int, user_id: int) -> None:
    game_state.setdefault(chat_id, {})['captain'] = user_id

def get_round(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).setdefault('round', 1)

def set_round(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['round'] = value

def get_question_index(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).setdefault('question_index', 0)

def set_question_index(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['question_index'] = value

def get_questions(chat_id: int) -> List[Any]:
    return game_state.setdefault(chat_id, {}).setdefault('questions', [])

def set_questions(chat_id: int, questions: List[Any]) -> None:
    game_state.setdefault(chat_id, {})['questions'] = questions

def get_answers(chat_id: int) -> List[str]:
    return game_state.setdefault(chat_id, {}).setdefault('answers', [])

def add_answer(chat_id: int, answer: str) -> None:
    game_state.setdefault(chat_id, {}).setdefault('answers', []).append(answer)

def reset_game(chat_id: int) -> None:
    game_state[chat_id] = {}

def get_total_score(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).setdefault('total_score', 0)

def add_to_total_score(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['total_score'] = get_total_score(chat_id) + value

def get_total_fast_bonus(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).setdefault('total_fast_bonus', 0)

def add_to_total_fast_bonus(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['total_fast_bonus'] = get_total_fast_bonus(chat_id) + value

def get_session_admin(chat_id: int) -> Optional[Tuple[int, str]]:
    return game_state.setdefault(chat_id, {}).get('session_admin')

def set_session_admin(chat_id: int, user_id: int, name: str) -> None:
    game_state.setdefault(chat_id, {})['session_admin'] = (user_id, name)

def get_difficulty(chat_id: int) -> str:
    return game_state.setdefault(chat_id, {}).get('difficulty', 'medium')

def set_difficulty(chat_id: int, value: str) -> None:
    game_state.setdefault(chat_id, {})['difficulty'] = value

def get_rounds(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).get('rounds', 3)

def set_rounds(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['rounds'] = value

def get_questions_per_round(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).get('questions_per_round', 5)

def set_questions_per_round(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['questions_per_round'] = value

def get_time_per_question(chat_id: int) -> int:
    return game_state.setdefault(chat_id, {}).get('time_per_question', 300)

def set_time_per_question(chat_id: int, value: int) -> None:
    game_state.setdefault(chat_id, {})['time_per_question'] = value

def get_fast_bonus_time(chat_id: int) -> int:
    time_per_question = get_time_per_question(chat_id)
    return max(1, int(time_per_question * 0.2))

# --- Кастомные фильтры ---
class ThemeStageFilter(filters.MessageFilter):
    def filter(self, message) -> bool:
        chat_id = message.chat.id
        return game_state.get(chat_id, {}).get('awaiting_theme', False)

class AnswerStageFilter(filters.MessageFilter):
    def filter(self, message) -> bool:
        chat_id = message.chat.id
        return game_state.get(chat_id, {}).get('awaiting_answer', False)

THEME_STAGE_FILTER = ThemeStageFilter()
ANSWER_STAGE_FILTER = AnswerStageFilter()

# --- Форматирование результатов ---
def format_round_results_individual(participants: Dict[int, str], score_by_user: Dict[int, int], fast_bonus_by_user: Dict[int, int], explanations_by_user: Dict[int, List[Dict[str, Any]]], chat_id=None) -> str:
    """Формирует текст результатов раунда для индивидуального режима."""
    sorted_participants = sorted(participants.items(), key=lambda x: (score_by_user[x[0]] + fast_bonus_by_user[x[0]]), reverse=True)
    text = f'🏁 Раунд завершён!\n\n'
    for pos, (uid, name) in enumerate(sorted_participants):
        total = score_by_user[uid]
        bonus = fast_bonus_by_user[uid]
        medal = lang.get_emoji('emoji_leader', chat_id) if pos < 3 else '⭐'
        text += f'{medal} {name}: {total} правильных, {bonus} бонусов (итого: {total+bonus})\n'
        for idx, r in enumerate(explanations_by_user[uid], 1):
            status = '✅' if r.get('correct') else '❌'
            explanation = r.get('explanation', '')
            correct_answer = r.get('correct_answer') or r.get('reference_answer') or ''
            text += f'    {status} Вопрос {idx}: {r.get("question")}\n    Ответ: {r.get("answer")}\n'
            if correct_answer:
                text += f'    Верный ответ: {correct_answer}\n'
            text += f'    Комментарий: {explanation}\n'
        text += '\n'
    return text

def format_round_results_team(results: List[Dict[str, Any]], correct: int, total: int, fast_bonus: int, fast_time: Optional[float], total_score: int, total_fast_bonus: int) -> str:
    """Формирует текст результатов раунда для командного режима."""
    text = f'�� Раунд завершён!\nПравильных ответов: {correct} из {total}\n'
    if fast_bonus:
        if fast_time is not None:
            text += f'⚡ Бонус за быстрый ответ (+1)! Ответ был дан за {int(fast_time)} секунд.\n'
        else:
            text += f'⚡ Бонус за быстрый ответ (+1)!\n'
    text += '\n'
    for i, r in enumerate(results, 1):
        status = '✅' if r.get('correct') else '❌'
        explanation = r.get('explanation', '')
        correct_answer = r.get('correct_answer') or r.get('reference_answer') or ''
        text += f'{status} Вопрос {i}: {r.get("question")}\nОтвет: {r.get("answer")}\n'
        if correct_answer:
            text += f'Верный ответ: {correct_answer}\n'
        text += f'Комментарий: {explanation}\n\n'
    total_points = total_score + total_fast_bonus
    text += f'⭐ Промежуточный счёт: {total_score} правильных ответов, {total_fast_bonus} бонусов (итого: {total_points} баллов) за все раунды.'
    return text

# --- Сообщение с настройками (единое для всех этапов) ---
async def send_settings_message(context, chat_id, stage, extra=None):
    """
    stage: 'mode', 'difficulty', 'rounds', 'questions', 'time', 'theme'
    extra: dict с выбранными настройками
    """
    if extra is None:
        extra = {}
    mode = extra.get('mode')
    difficulty = extra.get('difficulty')
    rounds = extra.get('rounds')
    questions = extra.get('questions')
    time_per_question = extra.get('time_per_question')
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
        keyboard = [[InlineKeyboardButton(str(r), callback_data=f'rounds_{r}')] for r in range(1, 6)]
    elif stage == 'questions':
        text = 'Выберите количество вопросов в раунде:'
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f'questions_{q}')] for q in range(3, 11)]
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id is None:
        return
    await send_settings_message(context, chat_id, 'mode')

async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    mode = query.data.split('_')[1]
    game_state.setdefault(chat_id, {})['mode'] = mode
    await send_settings_message(context, chat_id, 'difficulty', {'mode': mode})

async def difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    difficulty = query.data.split('_')[1]
    set_difficulty(chat_id, difficulty)
    await send_settings_message(context, chat_id, 'rounds', {'difficulty': difficulty})

async def theme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    theme = update.message.text.strip()
    if len(theme) < 2:
        await update.message.reply_text('Тема должна содержать минимум 2 символа.')
        return
    game_state[chat_id]['awaiting_theme'] = False
    game_state[chat_id]['theme'] = theme
    await send_registration_message(context, chat_id)

async def send_registration_message(context, chat_id, countdown: Optional[int] = None):
    participants = get_participants(chat_id)
    keyboard = [
        [InlineKeyboardButton('🎯 Присоединиться', callback_data='join')],
        [InlineKeyboardButton('�� Завершить регистрацию', callback_data='end_registration')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f'🎮 Регистрация участников\n\nУчастники ({len(participants)}):\n'
    for user_id, name in participants:
        text += f'• {name}\n'
    if countdown:
        text += f'\n⏰ Осталось: {countdown} сек'
    await context.bot.send_message(chat_id, text, reply_markup=reply_markup)

async def registration_timeout(context, chat_id, timeout):
    await context.bot.send_message(chat_id, f'⏰ Время регистрации истекло!')
    await end_registration(context, chat_id)

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    name = query.from_user.first_name or query.from_user.username or 'Неизвестный'
    participants = get_participants(chat_id)
    participants.add((user_id, name))
    await send_registration_message(context, chat_id)

async def end_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    await end_registration(context, chat_id)

async def end_registration(context, chat_id):
    participants = get_participants(chat_id)
    if len(participants) < 1:
        await context.bot.send_message(chat_id, '❌ Нужен минимум 1 участник для начала игры.')
        return
    await start_round(context, chat_id)

async def captain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    captain_id = int(query.data.split('_')[1])
    set_captain(chat_id, captain_id)
    await ask_next_question(context, chat_id)

async def start_round(context, chat_id):
    participants = get_participants(chat_id)
    mode = game_state.get(chat_id, {}).get('mode', 'team')
    if mode == 'team':
        await ask_next_question(context, chat_id)
    else:
        # Для индивидуального режима выбираем капитана
        keyboard = [[InlineKeyboardButton(name, callback_data=f'captain_{user_id}')] 
                   for user_id, name in participants]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, '👑 Выберите капитана команды:', reply_markup=reply_markup)

async def ask_next_question(context, chat_id):
    # Удаляем служебные сообщения, если есть
    if 'service_messages' in game_state.get(chat_id, {}):
        for msg_id in game_state[chat_id]['service_messages']:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except:
                pass
    game_state.setdefault(chat_id, {})['service_messages'] = []
    
    question_index = get_question_index(chat_id)
    questions_list = get_questions(chat_id)
    
    if question_index >= len(questions_list):
        await finish_round(context, chat_id)
        return
    
    question_data = questions_list[question_index]
    question_text = question_data['question']
    correct_answer = question_data['correct_answer']
    
    keyboard = [[InlineKeyboardButton('💬 Ответить', callback_data='answer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    time_per_question = get_time_per_question(chat_id)
    msg = await context.bot.send_message(
        chat_id, 
        f'❓ Вопрос {question_index + 1}:\n\n{question_text}\n\n⏰ Время: {time_per_question} сек',
        reply_markup=reply_markup
    )
    
    game_state[chat_id]['service_messages'].append(msg.message_id)
    game_state[chat_id]['awaiting_answer'] = True
    game_state[chat_id]['current_question'] = question_data
    game_state[chat_id]['question_start_time'] = time.time()
    
    # Запускаем таймер
    context.job_queue.run_once(
        lambda ctx: question_countdown(ctx, chat_id, time_per_question),
        time_per_question
    )

async def question_countdown(context, chat_id, timeout):
    if not game_state.get(chat_id, {}).get('awaiting_answer', False):
        return
    
    game_state[chat_id]['awaiting_answer'] = False
    current_question = game_state[chat_id].get('current_question', {})
    correct_answer = current_question.get('correct_answer', '')
    
    # Удаляем кнопку "Ответить"
    try:
        await context.bot.edit_message_reply_markup(
            chat_id, 
            game_state[chat_id]['service_messages'][-1],
            reply_markup=None
        )
    except:
        pass
    
    await context.bot.send_message(
        chat_id,
        f'⏰ Время истекло!\n\n✅ Правильный ответ: {correct_answer}'
    )
    
    # Добавляем результат
    add_answer(chat_id, '')
    add_to_total_score(chat_id, 0)
    
    # Переходим к следующему вопросу
    set_question_index(chat_id, get_question_index(chat_id) + 1)
    await ask_next_question(context, chat_id)

async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    game_state[chat_id]['awaiting_answer'] = False
    game_state[chat_id]['awaiting_text_answer'] = True
    await context.bot.send_message(chat_id, '�� Введите ваш ответ:')

async def answer_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if not game_state.get(chat_id, {}).get('awaiting_text_answer', False):
        return
    
    game_state[chat_id]['awaiting_text_answer'] = False
    user_answer = update.message.text.strip()
    
    current_question = game_state[chat_id].get('current_question', {})
    correct_answer = current_question.get('correct_answer', '')
    question_text = current_question.get('question', '')
    
    # Проверяем ответ
    is_correct = user_answer.lower() == correct_answer.lower()
    
    # Проверяем бонус за быстрый ответ
    start_time = game_state[chat_id].get('question_start_time', 0)
    answer_time = time.time() - start_time
    fast_bonus_time = get_fast_bonus_time(chat_id)
    fast_bonus = 0
    if is_correct and answer_time <= fast_bonus_time:
        fast_bonus = 1
        add_to_total_fast_bonus(chat_id, 1)
    
    # Добавляем результат
    add_answer(chat_id, user_answer)
    add_to_total_score(chat_id, 1 if is_correct else 0)
    
    # Формируем ответ
    status = '✅' if is_correct else '❌'
    bonus_text = f' ⚡ Бонус за быстрый ответ!' if fast_bonus else ''
    time_text = f' (за {int(answer_time)} сек)' if fast_bonus else ''
    
    await update.message.reply_text(
        f'{status} Ваш ответ: {user_answer}\n'
        f'Правильный ответ: {correct_answer}\n'
        f'{bonus_text}{time_text}'
    )
    
    # Переходим к следующему вопросу
    set_question_index(chat_id, get_question_index(chat_id) + 1)
    await ask_next_question(context, chat_id)

async def finish_round(context, chat_id):
    def remove_registration_buttons():
        # Удаляем кнопки регистрации
        pass
    
    participants = get_participants(chat_id)
    answers = get_answers(chat_id)
    questions_list = get_questions(chat_id)
    total_score = get_total_score(chat_id)
    total_fast_bonus = get_total_fast_bonus(chat_id)
    
    # Формируем результаты
    results = []
    correct_count = 0
    
    for i, (answer, question) in enumerate(zip(answers, questions_list)):
        is_correct = answer.lower() == question['correct_answer'].lower()
        if is_correct:
            correct_count += 1
        
        results.append({
            'question': question['question'],
            'answer': answer,
            'correct': is_correct,
            'correct_answer': question['correct_answer'],
            'explanation': question.get('explanation', '')
        })
    
    # Отправляем результаты
    result_text = format_round_results_team(
        results, correct_count, len(questions_list), 
        total_fast_bonus, None, total_score, total_fast_bonus
    )
    
    keyboard = [
        [InlineKeyboardButton('🔄 Следующий раунд', callback_data='next_round')],
        [InlineKeyboardButton('�� Показать рейтинг', callback_data='show_rating')],
        [InlineKeyboardButton('🚪 Выйти', callback_data='leave')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id, result_text, reply_markup=reply_markup)

async def next_round_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    set_round(chat_id, get_round(chat_id) + 1)
    set_question_index(chat_id, 0)
    set_questions(chat_id, [])
    set_answers(chat_id, [])
    await start_round(context, chat_id)

async def show_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    total_score = get_total_score(chat_id)
    total_fast_bonus = get_total_fast_bonus(chat_id)
    total_points = total_score + total_fast_bonus
    
    text = f'�� Итоговый рейтинг:\n\n'
    text += f'✅ Правильных ответов: {total_score}\n'
    text += f'⚡ Бонусов за скорость: {total_fast_bonus}\n'
    text += f'⭐ Общий счёт: {total_points} баллов'
    
    keyboard = [[InlineKeyboardButton('🚪 Выйти', callback_data='leave')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id, text, reply_markup=reply_markup)

async def leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    reset_game(chat_id)
    await context.bot.send_message(chat_id, '👋 Игра завершена! Используйте /start для новой игры.')

async def rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    rounds = int(query.data.split('_')[1])
    set_rounds(chat_id, rounds)
    await send_settings_message(context, chat_id, 'questions', {'rounds': rounds})

async def questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    questions_count = int(query.data.split('_')[1])
    set_questions_per_round(chat_id, questions_count)
    await send_settings_message(context, chat_id, 'time', {'questions': questions_count})

async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    time_per_question = int(query.data.split('_')[1])
    set_time_per_question(chat_id, time_per_question)
    await send_settings_message(context, chat_id, 'theme', {'time_per_question': time_per_question})

async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id is None:
        return
    reset_game(chat_id)
    await context.bot.send_message(chat_id, '👋 Игра завершена! Используйте /start для новой игры.')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id is None:
        return
    reset_game(chat_id)
    await context.bot.send_message(chat_id, '🛑 Игра остановлена! Используйте /start для новой игры.')

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id is None:
        return
    await context.bot.send_message(chat_id, '📰 Новости и обновления бота будут здесь!')

def get_questions_history(theme: str, limit: int = 50) -> list:
    return []

def add_question_to_history(theme: str, question: str):
    pass

def get_last_game_id(chat_id):
    return 0

def insert_answers(game_id, answers):
    pass

def insert_game_participants(game_id, participants):
    pass

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id is None:
        return
    keyboard = [["Русский", "English"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(chat_id, "Выберите язык / Choose language:", reply_markup=reply_markup)

async def lang_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update or not update.message:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    text = update.message.text.lower() if update.message.text else ''
    if "рус" in text:
        lang.set_language(chat_id, "ru")
        await update.message.reply_text("Язык переключён на русский ��🇺")
    elif "eng" in text:
        lang.set_language(chat_id, "en")
        await update.message.reply_text("Language switched to English 🇬🇧")
    else:
        await update.message.reply_text("Неизвестный язык / Unknown language")

async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    async with aiosqlite.connect('quizbot.db') as conn:
        async with conn.execute('SELECT COUNT(*) FROM games') as c:
            total_games = (await c.fetchone())[0]
        async with conn.execute('SELECT username, wins FROM users ORDER BY wins DESC, total_score DESC LIMIT 5') as c:
            top_wins = await c.fetchall()
        async with conn.execute('SELECT username, total_score FROM users ORDER BY total_score DESC, wins DESC LIMIT 5') as c:
            top_scores = await c.fetchall()
        async with conn.execute('SELECT theme, COUNT(*) as cnt FROM games GROUP BY theme ORDER BY cnt DESC LIMIT 5') as c:
            top_themes = await c.fetchall()
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

# --- Основная функция запуска ---
async def main():
    print('=== BOT STARTED ===')
    import sys
    print('Python version:', sys.version)
    
    print('DB INIT...')
    db.init_db()
    print('DB INIT DONE')
    
    print('Создаю Application...')
    app = ApplicationBuilder().token(TOKEN).build()
    print('Application создан')
    
    # Добавляем все обработчики
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('next', next_round_handler))
    app.add_handler(CommandHandler('exit', exit_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('news', news_command))
    app.add_handler(CommandHandler('stat', stat_command))
    app.add_handler(CallbackQueryHandler(mode_callback, pattern='^mode_'))
    app.add_handler(CallbackQueryHandler(difficulty_callback, pattern='^difficulty_'))
    app.add_handler(CallbackQueryHandler(rounds_callback, pattern='^rounds_'))
    app.add_handler(CallbackQueryHandler(questions_callback, pattern='^questions_'))
    app.add_handler(CallbackQueryHandler(time_callback, pattern='^time_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & THEME_STAGE_FILTER, theme_handler))
    app.add_handler(CallbackQueryHandler(join_callback, pattern='^join$'))
    app.add_handler(CallbackQueryHandler(end_registration_callback, pattern='^end_registration$'))
    app.add_handler(CallbackQueryHandler(captain_callback, pattern='^captain_'))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern='^answer$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ANSWER_STAGE_FILTER, answer_message_handler))
    app.add_handler(CallbackQueryHandler(show_rating_callback, pattern='^show_rating$'))
    app.add_handler(CallbackQueryHandler(leave_callback, pattern='^leave$'))
    app.add_handler(CommandHandler('lang', lang_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice_handler))
    
    print('Handlers добавлены, запускаю...')
    
    # Проверяем, запущены ли мы в Replit
    if 'REPL_SLUG' in os.environ:
        # Запуск в Replit - используем webhook
        REPL_URL = f"https://{os.environ['REPL_SLUG']}.{os.environ['REPL_OWNER']}.repl.co"
        WEBHOOK_PATH = f"/{TOKEN}"
        WEBHOOK_URL = REPL_URL + WEBHOOK_PATH
        print(f"Webhook URL: {WEBHOOK_URL}")
        
        await app.bot.set_webhook(WEBHOOK_URL)
        print("Webhook set:", WEBHOOK_URL)
        
        await app.run_webhook(
            listen="0.0.0.0",
            port=443,
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL,
        )
    else:
        # Запуск локально - используем polling
        try:
            await app.run_polling()
        except RuntimeError as e:
            print('Polling error:', e)
            if "already running" in str(e) or "Cannot close a running event loop" in str(e):
                print("[ERROR] PTB не может закрыть event loop. Запуск в этом окружении невозможен.")
                import sys
                sys.exit(1)
            else:
                raise
    
    print('Bot завершён')

# --- Запуск приложения ---
if __name__ == "__main__":
    asyncio.run(main())