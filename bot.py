# --- Импорты ---
import json
import asyncio
import logging
import re
import time
import random
from typing import Any, Dict, List, Set, Tuple, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
import aiohttp
from collections import defaultdict
import sqlite3
import os
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
    text = f'🏁 Раунд завершён!\nПравильных ответов: {correct} из {total}\n'
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
        text = 'Выберите количество вопросов в каждом раунде:'
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f'questions_{q}')] for q in range(3, 11)]
    elif stage == 'time':
        text = 'Выберите время на ответ для каждого вопроса:'
        keyboard = [
            [InlineKeyboardButton('1 мин', callback_data='time_60')],
            [InlineKeyboardButton('2 мин', callback_data='time_120')],
            [InlineKeyboardButton('3 мин', callback_data='time_180')],
            [InlineKeyboardButton('5 мин', callback_data='time_300')]
        ]
    # Добавить выбранные настройки в текст
    settings = []
    if mode:
        settings.append(f'<b>Режим:</b> {"Командный" if mode=="team" else "Индивидуальный"}')
    if difficulty:
        diff_str = {'easy': 'Легкий', 'medium': 'Средний', 'hard': 'Сложный'}.get(difficulty, difficulty)
        settings.append(f'<b>Сложность:</b> {diff_str}')
    if rounds:
        settings.append(f'<b>Раундов:</b> {rounds}')
    if questions:
        settings.append(f'<b>Вопросов в раунде:</b> {questions}')
    if time_per_question:
        settings.append(f'<b>Время на ответ:</b> {time_per_question//60} мин.')
    if settings:
        text += '\n\n<b>⚙️ Настройки:</b>\n' + '\n'.join(settings)
    msg_id = game_state[chat_id].get('settings_message_id')
    try:
        if msg_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            msg = await context.bot.send_message(
                chat_id,
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            game_state[chat_id]['settings_message_id'] = msg.message_id
    except Exception:
        # Если сообщение было удалено вручную — создаём новое
        msg = await context.bot.send_message(
            chat_id,
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        game_state[chat_id]['settings_message_id'] = msg.message_id

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else None
    user_name = update.effective_user.full_name if update.effective_user else None
    if user_id is None or user_name is None:
        await update.message.reply_text('Ошибка: не удалось определить пользователя.')
        return
    # Проверка на уже запущенную сессию
    if game_state.get(chat_id, {}).get('session_admin'):
        admin_id, admin_name = game_state[chat_id]['session_admin']
        await update.message.reply_text(f'Сессия уже запущена! Админ: {admin_name}. Дождитесь окончания или попросите админа завершить игру.')
        return
    reset_game(chat_id)
    set_session_admin(chat_id, user_id, user_name)
    # --- Выбор режима игры ---
    await send_settings_message(context, chat_id, 'mode')
    game_state[chat_id]['awaiting_mode'] = True

async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может выбрать режим!', show_alert=True)
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('mode_'):
        return
    mode = 'team' if data == 'mode_team' else 'individual'
    game_state[chat_id]['mode'] = mode
    game_state[chat_id]['awaiting_mode'] = False
    await query.answer(f'Режим выбран: {"Командный" if mode=="team" else "Каждый сам за себя"}')
    await send_settings_message(context, chat_id, 'difficulty', extra={'mode': mode})
    game_state[chat_id]['awaiting_difficulty'] = True

async def difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может выбрать сложность!', show_alert=True)
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('difficulty_'):
        return
    difficulty = data.split('_')[1]
    set_difficulty(chat_id, difficulty)
    game_state[chat_id]['awaiting_difficulty'] = False
    mode = game_state[chat_id].get('mode')
    await query.answer(f'Сложность выбрана: {"Легкий" if difficulty=="easy" else ("Средний" if difficulty=="medium" else "Сложный")}')
    await send_settings_message(context, chat_id, 'rounds', extra={'mode': mode, 'difficulty': difficulty})
    game_state[chat_id]['awaiting_rounds'] = True

async def theme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else None
    admin = get_session_admin(chat_id)
    if not game_state.get(chat_id, {}).get('awaiting_theme'):
        return
    if not admin or user_id != admin[0]:
        await update.message.reply_text('Только админ может выбрать тему!')
        return
    theme = update.message.text.strip()
    game_state[chat_id]['theme'] = theme
    game_state[chat_id]['awaiting_theme'] = False
    game_state[chat_id]['registration'] = True
    game_state[chat_id]['participants'] = set()
    await send_registration_message(context, chat_id)
    # 1 минута на регистрацию
    asyncio.create_task(registration_timeout(context, chat_id, 60))

async def send_registration_message(context, chat_id, countdown: Optional[int] = None):
    if 'theme' not in game_state.get(chat_id, {}):
        await context.bot.send_message(chat_id, "Тема квиза ещё не выбрана. Сначала выберите тему!")
        return
    participants = get_participants(chat_id)
    theme = game_state[chat_id]['theme']
    players = ''
    lang_code = lang.get_language(chat_id)
    emoji_list = LANGUAGES[lang_code]['emoji_player']
    for i, (_, name) in enumerate(participants):
        emoji = emoji_list[i % len(emoji_list)]
        players += f'{emoji} {name}\n'
    # --- Информация о настройках ---
    mode = game_state[chat_id].get('mode', 'team')
    difficulty = get_difficulty(chat_id)
    rounds = get_rounds(chat_id)
    questions_per_round = get_questions_per_round(chat_id)
    time_per_question = get_time_per_question(chat_id)
    mode_str = 'Командный' if mode == 'team' else 'Индивидуальный'
    diff_str = {'easy': 'Легкий', 'medium': 'Средний', 'hard': 'Сложный'}.get(difficulty, difficulty)
    settings_text = (
        f'<b>⚙️ Настройки игры:</b>\n'
        f'<b>Режим:</b> {mode_str}\n'
        f'<b>Сложность:</b> {diff_str}\n'
        f'<b>Раундов:</b> {rounds}\n'
        f'<b>Вопросов в раунде:</b> {questions_per_round}\n'
        f'<b>Время на ответ:</b> {time_per_question//60} мин.'
    )
    text = (
        f'📚 <b>Тема квиза:</b> {theme}\n\n'
        f'Нажмите "Участвовать", чтобы присоединиться!\n'
        f'Когда все готовы — нажмите "Начать игру".'
        f'\n\n{settings_text}'
    )
    if players:
        text += f'\n\n<b>Участники:</b>\n{players}'
    # Кнопка с обратным отсчётом
    if countdown is not None:
        btn_text = f'Начать игру ({countdown:02d} сек)' if countdown > 0 else 'Начать игру'
    else:
        btn_text = 'Начать игру'
    keyboard = [[InlineKeyboardButton('Участвовать', callback_data='join')]]
    keyboard.append([InlineKeyboardButton(btn_text, callback_data='end_registration')])
    keyboard.append([InlineKeyboardButton('Показать рейтинг', callback_data='show_rating')])
    keyboard.append([InlineKeyboardButton('Выйти из игры', callback_data='leave')])
    msg_id = game_state[chat_id].get('registration_message_id')
    if msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception:
            # Если сообщение было удалено вручную — создаём новое
            msg = await context.bot.send_message(
                chat_id,
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            game_state[chat_id]['registration_message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(
            chat_id,
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        game_state[chat_id]['registration_message_id'] = msg.message_id

async def registration_timeout(context, chat_id, timeout):
    for t in range(timeout, 0, -5):
        if not game_state.get(chat_id, {}).get('registration', False):
            return
        await send_registration_message(context, chat_id, countdown=t)
        await asyncio.sleep(5)
    # Последний раз обновить кнопку без таймера
    if game_state.get(chat_id, {}).get('registration', False):
        await send_registration_message(context, chat_id, countdown=0)
        await end_registration(context, chat_id)

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    print(f"[LOG] join_callback: data={getattr(query, 'data', None)}, user={getattr(getattr(query, 'from_user', None), 'full_name', None)}")
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user = query.from_user
    participants = get_participants(chat_id)
    # Проверка: если уже зарегистрирован — не добавлять повторно
    if any(uid == user.id for uid, _ in participants):
        await query.answer('Вы уже зарегистрированы!')
        return
    participants.add((user.id, user.full_name))
    await query.answer(f'Вы зарегистрированы: {user.full_name}')
    await send_registration_message(context, chat_id)

async def end_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может завершить регистрацию!', show_alert=True)
        return
    # Защита от двойного нажатия
    if not game_state.get(chat_id, {}).get('registration', False):
        await query.answer('Регистрация уже завершена!', show_alert=True)
        return
    await end_registration(context, chat_id)
    await query.answer('Регистрация завершена!')

async def end_registration(context, chat_id):
    game_state[chat_id]['registration'] = False
    # Оставляем сообщение регистрации в чате, не удаляем его
    participants = list(get_participants(chat_id))
    if not participants:
        await context.bot.send_message(chat_id, 'Нет участников. Игра отменена.')
        reset_game(chat_id)
        return
    mode = game_state[chat_id].get('mode', 'team')
    if mode == 'team':
        # Выбор капитана
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f'captain_{uid}')]
            for uid, name in participants
        ]
        msg = await context.bot.send_message(
            chat_id,
            'Выберите капитана команды (нажмите на имя):',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        game_state[chat_id]['captain_message_id'] = msg.message_id
    else:
        # Индивидуальный режим — сразу стартуем раунд
        msg = await context.bot.send_message(chat_id, 'Регистрация завершена! Начинаем игру в индивидуальном режиме 🧑‍🎓')
        game_state[chat_id]['indiv_start_message_id'] = msg.message_id
        await start_round(context, chat_id)

async def captain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('captain_'):
        return
    uid = int(data.split('_')[1])
    set_captain(chat_id, uid)
    await query.answer('Выбран капитан!')
    await context.bot.send_message(chat_id, f'Капитан: {query.from_user.full_name}')
    await start_round(context, chat_id)

async def start_round(context, chat_id):
    round_num = get_round(chat_id)
    theme = game_state[chat_id]['theme']
    msg = await context.bot.send_message(chat_id, f'Генерирую вопросы для раунда {round_num}...')
    game_state[chat_id]['gen_questions_message_id'] = msg.message_id
    questions_list = await questions.openai_generate_questions(theme, round_num, chat_id, get_difficulty, get_questions_per_round)
    set_questions(chat_id, questions_list)
    set_question_index(chat_id, 0)
    game_state[chat_id]['answers'] = []
    # --- Сброс индивидуальных ответов для нового раунда ---
    if game_state[chat_id].get('mode', 'team') == 'individual':
        game_state[chat_id]['individual_answers'] = {}
    await ask_next_question(context, chat_id)

async def ask_next_question(context, chat_id):
    # Удаляем служебные сообщения, если есть
    for key in ['indiv_start_message_id', 'gen_questions_message_id']:
        msg_id = game_state[chat_id].pop(key, None)
        if msg_id:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
    questions = get_questions(chat_id)
    idx = get_question_index(chat_id)
    if idx >= len(questions):
        game_state[chat_id]['awaiting_answer'] = False
        await finish_round(context, chat_id)
        return
    q = questions[idx]
    if isinstance(q, str):
        question_text = q
        difficulty = None
    else:
        question_text = q.get('question', str(q))
        difficulty = q.get('difficulty')
    mode = game_state[chat_id].get('mode', 'team')
    time_per_question = get_time_per_question(chat_id)
    time_str = f'{time_per_question//60} минута' if time_per_question == 60 else f'{time_per_question//60} минуты' if time_per_question in (120, 180) else f'{time_per_question//60} минут'
    if mode == 'individual':
        text = (
            f'❓ <b>Вопрос {idx+1}</b>\n\n'
            f'<b>{question_text}</b>\n\n'
            f'✍️ <i>Ответьте на это сообщение реплаем!</i>\n'
            f'⏳ <b>Время на обсуждение:</b> {time_str}'
        )
        msg = await context.bot.send_message(
            chat_id,
            text,
            parse_mode='HTML'
        )
        game_state[chat_id]['current_question_message_id'] = msg.message_id
        game_state[chat_id]['answer_message_id'] = msg.message_id
        game_state[chat_id]['question_start_time'] = time.time()
        game_state[chat_id]['awaiting_answer'] = True
        asyncio.create_task(question_countdown(context, chat_id, time_per_question))
        return
    # --- командный режим ---
    captain_id = get_captain(chat_id)
    keyboard = [[InlineKeyboardButton('Ответить', callback_data='answer')]]
    text = (
        f'❓ <b>Вопрос {idx+1}</b>\n\n'
        f'<b>{question_text}</b>\n\n'
        f'👥 <i>Обсудите в команде и нажмите "Ответить", когда будете готовы</i>\n'
        f'⏳ <b>Время на обсуждение:</b> {time_str}'
    )
    msg = await context.bot.send_message(
        chat_id,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    await context.bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
    game_state[chat_id]['current_question_message_id'] = msg.message_id
    game_state[chat_id]['question_start_time'] = time.time()
    asyncio.create_task(question_countdown(context, chat_id, time_per_question))

async def question_countdown(context, chat_id, timeout):
    try:
        if timeout > 60:
            await asyncio.sleep(timeout - 60)
            if not game_state.get(chat_id, {}).get('awaiting_answer', False):
                return
            await context.bot.send_message(chat_id, f'⏳ Осталась 1 минута на обсуждение!')
            await asyncio.sleep(50)
            if not game_state.get(chat_id, {}).get('awaiting_answer', False):
                return
            await context.bot.send_message(chat_id, f'⚡ Осталось 10 секунд!')
            await asyncio.sleep(10)
            if not game_state.get(chat_id, {}).get('awaiting_answer', False):
                return
        else:
            await asyncio.sleep(timeout)
            if not game_state.get(chat_id, {}).get('awaiting_answer', False):
                return
        if not game_state.get(chat_id, {}).get('awaiting_answer', False):
            return
        idx = get_question_index(chat_id)
        questions = get_questions(chat_id)
        mode = game_state[chat_id].get('mode', 'team')
        if idx < len(questions):
            if mode == 'team':
                await context.bot.send_message(chat_id, '⏰ Время на обсуждение истекло! Ответ не получен, вопрос пропущен.')
                game_state[chat_id]['awaiting_answer'] = False
                set_question_index(chat_id, idx+1)
                await ask_next_question(context, chat_id)
            else:
                await context.bot.send_message(chat_id, '⏰ Время на обсуждение истекло! Можно отвечать, но без бонуса за скорость.')
                # Автоматически переходим к следующему вопросу, если все уже ответили или никто не ответил
                participants = {uid for uid, _ in get_participants(chat_id)}
                individual_answers = game_state[chat_id].get('individual_answers', {})
                if idx not in individual_answers:
                    individual_answers[idx] = {}
                answered = set(individual_answers[idx].keys())
                # Пропускаем неотвеченных
                for uid in participants - answered:
                    individual_answers[idx][uid] = {
                        'answer': '',
                        'fast_bonus': 0,
                        'fast_time': None,
                        'name': ''
                    }
                game_state[chat_id]['awaiting_answer'] = False
                set_question_index(chat_id, idx+1)
                await ask_next_question(context, chat_id)
    except Exception as e:
        print('[LOG] Ошибка в таймере вопроса:', e)

async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    captain_id = get_captain(chat_id)
    if user_id != captain_id:
        await query.answer('Только капитан может отправить ответ!', show_alert=True)
        return
    await query.answer()
    # Сохраняем message_id сообщения, на которое нужно делать reply
    msg = await context.bot.send_message(chat_id, 'Пожалуйста, отправьте ваш ответ на этот вопрос одним сообщением.')
    game_state[chat_id]['awaiting_answer'] = True
    game_state[chat_id]['answer_message_id'] = msg.message_id

async def answer_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('[LOG] answer_message_handler called')
    if not update.message or not update.effective_chat or not update.effective_user or not update.message.text:
        print('[LOG] Пропуск: нет message, effective_chat, effective_user или текста')
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f'[LOG] chat_id={chat_id}, user_id={user_id}')
    mode = game_state.get(chat_id, {}).get('mode', 'team')
    if not game_state.get(chat_id, {}).get('awaiting_answer'):
        print('[LOG] Пропуск: not awaiting_answer')
        return
    # --- Индивидуальный режим ---
    if mode == 'individual':
        participants = {uid for uid, _ in get_participants(chat_id)}
        if user_id not in participants:
            print('[LOG] Пропуск: user_id не зарегистрирован')
            return
        answer_msg_id = game_state[chat_id].get('answer_message_id')
        reply_msg_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None
        if not update.message.reply_to_message or reply_msg_id != answer_msg_id:
            print('[LOG] Пропуск: ответ не reply на нужное сообщение')
            return
        answer = update.message.text.strip()
        idx = get_question_index(chat_id)
        if 'individual_answers' not in game_state[chat_id]:
            game_state[chat_id]['individual_answers'] = {}
        if idx not in game_state[chat_id]['individual_answers']:
            game_state[chat_id]['individual_answers'][idx] = {}
        if user_id in game_state[chat_id]['individual_answers'][idx]:
            print('[LOG] Пропуск: пользователь уже ответил на этот вопрос')
            return
        start_time = game_state[chat_id].get('question_start_time')
        answer_time = time.time()
        fast_bonus = 0
        if start_time:
            elapsed = answer_time - start_time
            if elapsed <= get_fast_bonus_time(chat_id):
                fast_bonus = 1
            else:
                fast_bonus = 0
        game_state[chat_id]['individual_answers'][idx][user_id] = {
            'answer': answer,
            'fast_bonus': fast_bonus,
            'fast_time': elapsed if start_time else None,
            'name': update.effective_user.full_name
        }
        print(f'[LOG] Индивидуальный ответ принят: {user_id} -> {answer}')
        await update.message.reply_text('✅ Ответ принят! ' + random.choice(lang.get_text('feedback_good', chat_id)))
        answered = set(game_state[chat_id]['individual_answers'][idx].keys())
        if answered == participants:
            game_state[chat_id]['awaiting_answer'] = False
            set_question_index(chat_id, idx+1)
            await ask_next_question(context, chat_id)
        return
    # --- Командный режим ---
    captain_id = get_captain(chat_id)
    print(f'[LOG] captain_id={captain_id}')
    if user_id != captain_id:
        print('[LOG] Пропуск: user_id != captain_id')
        return
    answer_msg_id = game_state[chat_id].get('answer_message_id')
    reply_msg_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None
    print(f'[LOG] answer_msg_id={answer_msg_id}, reply_msg_id={reply_msg_id}')
    if not update.message.reply_to_message or reply_msg_id != answer_msg_id:
        print('[LOG] Пропуск: ответ не reply на нужное сообщение')
        return
    answer = update.message.text.strip()
    print(f'[LOG] Ответ принят: {answer}')
    add_answer(chat_id, answer)
    game_state[chat_id]['awaiting_answer'] = False
    # --- Бонус за быстрый ответ ---
    start_time = game_state[chat_id].get('question_start_time')
    answer_time = time.time()
    fast_bonus = 0
    if start_time:
        elapsed = answer_time - start_time
        if elapsed <= get_fast_bonus_time(chat_id):
            fast_bonus = 1
            game_state[chat_id]['last_fast_bonus'] = 1
            game_state[chat_id]['last_fast_time'] = elapsed
        else:
            game_state[chat_id]['last_fast_bonus'] = 0
            game_state[chat_id]['last_fast_time'] = elapsed
    # Unpin вопрос
    msg_id = game_state[chat_id].get('current_question_message_id')
    if msg_id:
        try:
            await context.bot.unpin_chat_message(chat_id, msg_id)
        except Exception:
            pass
    # Следующий вопрос
    idx = get_question_index(chat_id)
    set_question_index(chat_id, idx+1)
    await ask_next_question(context, chat_id)

async def finish_round(context, chat_id):
    theme = game_state[chat_id]['theme']
    questions_list = get_questions(chat_id)
    mode = game_state[chat_id].get('mode', 'team')
    def remove_registration_buttons():
        msg_id = game_state.get(chat_id, {}).get('registration_message_id')
        if msg_id:
            try:
                import asyncio
                coro = context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
                if asyncio.iscoroutine(coro):
                    asyncio.create_task(coro)
            except Exception:
                pass
    if mode == 'individual':
        # Индивидуальный режим: собираем ответы всех участников
        participants = {uid: name for uid, name in get_participants(chat_id)}
        answers_by_user = {uid: [] for uid in participants}
        fast_bonus_by_user = {uid: 0 for uid in participants}
        # Для каждого вопроса собираем ответы
        individual_answers = game_state[chat_id].get('individual_answers', {})
        qa_pairs = []
        user_for_qa = []  # user_id для каждого ответа
        for idx, q in enumerate(questions_list):
            ans_dict = individual_answers.get(idx, {})
            for uid in participants:
                ans = ans_dict.get(uid)
                if ans:
                    qa_pairs.append({"question": q["question"] if isinstance(q, dict) else str(q), "answer": ans["answer"]})
                    user_for_qa.append(uid)
                else:
                    qa_pairs.append({"question": q["question"] if isinstance(q, dict) else str(q), "answer": ""})
                    user_for_qa.append(uid)
        # Проверяем все ответы разом
        results = await questions.openai_check_answers(theme, [qa["question"] for qa in qa_pairs], [qa["answer"] for qa in qa_pairs])
        # Считаем баллы по каждому участнику
        score_by_user = {uid: 0 for uid in participants}
        explanations_by_user = {uid: [] for uid in participants}
        for i, r in enumerate(results):
            uid = user_for_qa[i]
            ans_dict = individual_answers.get(i // len(participants), {})
            ans = ans_dict.get(uid)
            if r.get("correct"):
                score_by_user[uid] += 1
                # Бонус только если ответ был быстрым и правильным
                if ans and ans.get("fast_bonus"):
                    fast_bonus_by_user[uid] += 1
            explanations_by_user[uid].append(r)
        # Выводим рейтинг
        text = f'🏁 Раунд завершён!\n\n'
        # Сортируем по баллам
        sorted_participants = sorted(participants.items(), key=lambda x: (score_by_user[x[0]] + fast_bonus_by_user[x[0]]), reverse=True)
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
        await context.bot.send_message(chat_id, text)
        # Сохраняем общий счёт по пользователям в game_state
        if 'individual_total_score' not in game_state[chat_id]:
            game_state[chat_id]['individual_total_score'] = {uid: 0 for uid in participants}
        if 'individual_total_bonus' not in game_state[chat_id]:
            game_state[chat_id]['individual_total_bonus'] = {uid: 0 for uid in participants}
        for uid in participants:
            game_state[chat_id]['individual_total_score'][uid] += score_by_user[uid]
            game_state[chat_id]['individual_total_bonus'][uid] += fast_bonus_by_user[uid]
        # Следующий раунд или конец игры
        round_num = get_round(chat_id)
        total_rounds = get_rounds(chat_id)
        if round_num < total_rounds:
            set_round(chat_id, round_num+1)
            await context.bot.send_message(chat_id, f'👉 Готовы к следующему раунду? Напишите "/next"')
            game_state[chat_id]['awaiting_next'] = True
        else:
            # Финальный рейтинг
            text = '🏆 Квиз завершён! Спасибо за игру!\n\nФинальный рейтинг:\n'
            sorted_final = sorted(participants.items(), key=lambda x: (game_state[chat_id]['individual_total_score'][x[0]] + game_state[chat_id]['individual_total_bonus'][x[0]]), reverse=True)
            for pos, (uid, name) in enumerate(sorted_final):
                total = game_state[chat_id]['individual_total_score'][uid]
                bonus = game_state[chat_id]['individual_total_bonus'][uid]
                medal = lang.get_emoji('emoji_leader', chat_id) if pos < 3 else '⭐'
                text += f'{medal} {name}: {total} правильных, {bonus} бонусов (итого: {total+bonus})\n'
            winner = sorted_final[0][1] if sorted_final else ''
            winner_id = sorted_final[0][0] if sorted_final else None
            text += f'\n🎉 Поздравляем победителя: {winner}!'
            await context.bot.send_message(chat_id, text)
            # --- Обновление статистики ---
            for uid, name in participants.items():
                score = game_state[chat_id]['individual_total_score'][uid] + game_state[chat_id]['individual_total_bonus'][uid]
                db.update_user_stats(uid, name, score, win=(winner_id is not None and uid == winner_id))
            if winner_id is not None:
                db.add_game_stat(chat_id, theme, mode, get_rounds(chat_id), get_questions_per_round(chat_id), winner_id)
            # --- Сохраняем расширенную статистику ---
            game_id = db.get_last_game_id(chat_id)
            if game_id is not None:
                # Сохраняем ответы
                answer_rows = []
                for idx, q in enumerate(questions_list):
                    ans_dict = individual_answers.get(idx, {}) if 'individual_answers' in locals() and individual_answers else {}
                    for uid in participants if participants else []:
                        ans = ans_dict.get(uid) if ans_dict else None
                        answer_rows.append({
                            'user_id': uid,
                            'question': q["question"] if isinstance(q, dict) else str(q),
                            'answer_text': ans["answer"] if ans else '',
                            'correct': explanations_by_user[uid][idx]["correct"] if uid in explanations_by_user and idx < len(explanations_by_user[uid]) else 0,
                            'fast_bonus': ans["fast_bonus"] if ans else 0,
                            'time_to_answer': ans["fast_time"] if ans and "fast_time" in ans else None
                        })
                db.insert_answers(game_id, answer_rows)
                # Сохраняем участников
                sorted_final = sorted(participants.items(), key=lambda x: (game_state[chat_id]['individual_total_score'][x[0]] + game_state[chat_id]['individual_total_bonus'][x[0]]), reverse=True)
                participant_rows = []
                for place, (uid, name) in enumerate(sorted_final, 1):
                    participant_rows.append({
                        'user_id': uid,
                        'score': game_state[chat_id]['individual_total_score'][uid],
                        'fast_bonus': game_state[chat_id]['individual_total_bonus'][uid],
                        'place': place
                    })
                db.insert_game_participants(game_id, participant_rows)
            remove_registration_buttons()
            reset_game(chat_id)
            return
    # --- Командный режим ---
    answers = get_answers(chat_id)
    await context.bot.send_message(chat_id, 'Раунд окончен, проверяются ответы...')
    results = await questions.openai_check_answers(theme, questions_list, answers)
    # --- Исправление: проверка результата ---
    if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
        await context.bot.send_message(chat_id, 'Ошибка проверки ответов AI. Попробуйте ещё раз или смените вопрос.')
        print('[LOG] Ошибка: некорректный формат ответа от OpenAI:', results)
        return
    correct = sum(1 for r in results if r.get('correct'))
    total = len(questions_list)
    # --- Бонусы за быстрый ответ ---
    fast_bonus = 0
    fast_time = game_state[chat_id].get('last_fast_time')
    if game_state[chat_id].get('last_fast_bonus') and results and results[0].get('correct'):
        fast_bonus = 1
    # --- Добавляем к отдельному счётчику бонусов ---
    add_to_total_score(chat_id, correct)
    add_to_total_fast_bonus(chat_id, fast_bonus)
    total_score = get_total_score(chat_id)
    total_fast_bonus = get_total_fast_bonus(chat_id)
    text = f'🏁 Раунд завершён!\nПравильных ответов: {correct} из {total}\n'
    if fast_bonus:
        text += f'⚡ Бонус за быстрый ответ (+1)! Ответ был дан за {int(fast_time)} секунд.\n'
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
    await context.bot.send_message(chat_id, text)
    # Следующий раунд или конец игры
    round_num = get_round(chat_id)
    total_rounds = get_rounds(chat_id)
    if round_num < total_rounds:
        set_round(chat_id, round_num+1)
        await context.bot.send_message(chat_id, f'👉 Готовы к следующему раунду? Напишите "/next"')
        game_state[chat_id]['awaiting_next'] = True
    else:
        await context.bot.send_message(chat_id, f'🏆 Квиз завершён! Спасибо за игру!\n\nОбщий результат: {total_score} правильных ответов, {total_fast_bonus} бонусов (итого: {total_points} баллов) за все раунды!')
        # --- Обновление статистики для капитана ---
        captain_id = get_captain(chat_id)
        participants = get_participants(chat_id)
        captain_name = None
        for uid, name in participants:
            if uid == captain_id:
                captain_name = name
                break
        if captain_id and captain_name:
            db.update_user_stats(captain_id, captain_name, total_score + total_fast_bonus, win=True)
        db.add_game_stat(chat_id, theme, mode, get_rounds(chat_id), get_questions_per_round(chat_id), captain_id)
        # --- Сохраняем расширенную статистику ---
        game_id = db.get_last_game_id(chat_id)
        if game_id is not None:
            # Сохраняем ответы (только капитан отвечает)
            answer_rows = []
            for idx, q in enumerate(questions_list):
                answer_rows.append({
                    'user_id': captain_id,
                    'question': q["question"] if isinstance(q, dict) else str(q),
                    'answer_text': answers[idx] if idx < len(answers) else '',
                    'correct': results[idx]["correct"] if idx < len(results) else 0,
                    'fast_bonus': fast_bonus if idx == 0 else 0,  # только за первый вопрос
                    'time_to_answer': fast_time if idx == 0 else None
                })
            db.insert_answers(game_id, answer_rows)
            # Сохраняем участников (капитан — 1 место, остальные — 2+)
            participant_rows = []
            place = 1
            for uid, name in participants:
                participant_rows.append({
                    'user_id': uid,
                    'score': total_score if uid == captain_id else 0,
                    'fast_bonus': total_fast_bonus if uid == captain_id else 0,
                    'place': place if uid == captain_id else 2
                })
            db.insert_game_participants(game_id, participant_rows)
        remove_registration_buttons()
        reset_game(chat_id)
        return

async def next_round_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if not game_state.get(chat_id, {}).get('awaiting_next'):
        return
    game_state[chat_id]['awaiting_next'] = False
    await start_round(context, chat_id)

# --- Кнопки "Показать рейтинг" и "Выйти из игры" ---
async def show_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    mode = game_state.get(chat_id, {}).get('mode', 'team')
    if mode == 'individual':
        participants = {uid: name for uid, name in get_participants(chat_id)}
        if 'individual_total_score' not in game_state[chat_id]:
            await query.answer('Рейтинг пока недоступен')
            return
        text = '⭐ Текущий рейтинг:\n'
        sorted_final = sorted(participants.items(), key=lambda x: (game_state[chat_id]['individual_total_score'][x[0]] + game_state[chat_id]['individual_total_bonus'][x[0]]), reverse=True)
        for pos, (uid, name) in enumerate(sorted_final):
            total = game_state[chat_id]['individual_total_score'][uid]
            bonus = game_state[chat_id]['individual_total_bonus'][uid]
            medal = lang.get_emoji('emoji_leader', chat_id) if pos < 3 else '⭐'
            text += f'{medal} {name}: {total} правильных, {bonus} бонусов (итого: {total+bonus})\n'
        await query.answer()
        await context.bot.send_message(chat_id, text)
    else:
        total_score = get_total_score(chat_id)
        total_fast_bonus = get_total_fast_bonus(chat_id)
        total_points = total_score + total_fast_bonus
        text = f'⭐ Командный счёт: {total_score} правильных, {total_fast_bonus} бонусов (итого: {total_points})'
        await query.answer()
        await context.bot.send_message(chat_id, text)
async def leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if admin and user_id == admin[0]:
        await query.answer('Админ не может покинуть игру!')
        return
    participants = get_participants(chat_id)
    before = len(participants)
    participants_copy = set(participants)
    for uid, name in participants_copy:
        if uid == user_id:
            participants.remove((uid, name))
    after = len(participants)
    await query.answer('Вы покинули игру.' if after < before else 'Вы не были в игре.')
    await send_registration_message(context, chat_id)

# --- Новый callback для выбора количества раундов ---
async def rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может выбрать количество раундов!', show_alert=True)
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('rounds_'):
        return
    rounds = int(data.split('_')[1])
    set_rounds(chat_id, rounds)
    mode = game_state[chat_id].get('mode')
    difficulty = get_difficulty(chat_id)
    await query.answer(f'Количество раундов: {rounds}')
    await send_settings_message(context, chat_id, 'questions', extra={'mode': mode, 'difficulty': difficulty, 'rounds': rounds})
    game_state[chat_id]['awaiting_questions_per_round'] = True

# --- Новый callback для выбора количества вопросов ---
async def questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может выбрать количество вопросов!', show_alert=True)
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('questions_'):
        return
    questions = int(data.split('_')[1])
    set_questions_per_round(chat_id, questions)
    mode = game_state[chat_id].get('mode')
    difficulty = get_difficulty(chat_id)
    rounds = get_rounds(chat_id)
    await query.answer(f'В каждом раунде будет {questions} вопросов')
    await send_settings_message(context, chat_id, 'time', extra={'mode': mode, 'difficulty': difficulty, 'rounds': rounds, 'questions': questions})
    game_state[chat_id]['awaiting_time_per_question'] = True

# --- Новый callback для выбора времени на вопрос ---
async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    chat = getattr(query, 'message', None)
    chat_obj = getattr(chat, 'chat', None)
    chat_id = chat_obj.id if chat_obj else None
    if chat_id is None:
        return
    user_id = getattr(getattr(query, 'from_user', None), 'id', None)
    admin = get_session_admin(chat_id)
    if not admin or user_id != admin[0]:
        await query.answer('Только админ может выбрать время на вопрос!', show_alert=True)
        return
    data = getattr(query, 'data', None)
    if not data or not data.startswith('time_'):
        return
    seconds = int(data.split('_')[1])
    set_time_per_question(chat_id, seconds)
    mode = game_state[chat_id].get('mode')
    difficulty = get_difficulty(chat_id)
    rounds = get_rounds(chat_id)
    questions = get_questions_per_round(chat_id)
    await query.answer(f'Время на вопрос: {seconds//60} мин.')
    # Удаляем сообщение с настройками
    msg_id = game_state[chat_id].get('settings_message_id')
    if msg_id:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        game_state[chat_id]['settings_message_id'] = None
    await context.bot.send_message(chat_id, 'Введите тему квиза (например, "История России"):' )
    game_state[chat_id]['awaiting_theme'] = True

# --- Голосование за остановку ---
stop_votes = defaultdict(set)  # chat_id -> set(user_id)

async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    admin = get_session_admin(chat_id)
    if admin and user_id == admin[0]:
        await update.message.reply_text('Админ не может выйти из сессии. Используйте /stop для завершения игры.')
        return
    participants = get_participants(chat_id)
    before = len(participants)
    participants_copy = set(participants)
    for uid, name in participants_copy:
        if uid == user_id:
            participants.remove((uid, name))
    after = len(participants)
    if after < before:
        await update.message.reply_text('Вы покинули игру.')
        await send_registration_message(context, chat_id)
    else:
        await update.message.reply_text('Вы не были в игре.')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    admin = get_session_admin(chat_id)
    participants = {uid for uid, _ in get_participants(chat_id)}
    if admin and user_id == admin[0]:
        await update.message.reply_text('Сессия завершена админом.')
        reset_game(chat_id)
        return
    # Не админ — запускаем голосование
    stop_votes[chat_id].add(user_id)
    votes = len(stop_votes[chat_id])
    total = len(participants)
    if votes > total // 2:
        await update.message.reply_text('Большинство проголосовало за завершение сессии. Игра остановлена.')
        reset_game(chat_id)
        stop_votes[chat_id].clear()
    else:
        await update.message.reply_text(f'Голосование за остановку игры: {votes}/{total} голосов. Для остановки нужно больше половины.')

# --- Main ---
VERSION = '1.6.0'
CHANGELOG = '''
Версия 1.6.0 (июль 2025):
- Вся работа с базой данных теперь полностью асинхронная (aiosqlite).
- Существенно ускорена обработка команд и статистики, бот готов к масштабированию.
- Исправлены все возможные ошибки обращения к несуществующим данным в статистике и истории.
- Удалены все синхронные вызовы sqlite3, код стал чище и безопаснее.
- Мелкие улучшения UX и стабильности.

Версия 1.5.2 (июль 2025):
- До старта игры используется только одно сообщение регистрации, оно редактируется и удаляется после старта/отмены (чат остаётся чистым).
- Улучшена статистика: теперь сохраняется больше информации о сыгранных играх и участниках.

Версия 1.5.1 (июнь 2025):
- Исправлено: если время на вопрос ≤ 1 мин, напоминания о 1 минуте и 10 секундах не отправляются, только финальное сообщение.
- Добавлена команда /stat — можно посмотреть статистику по играм и игрокам.
- Добавлена команда /news — можно узнать историю изменений.

Версия 1.5.0 (июнь 2025):
- Появились команды /exit (выход из игры) и /stop (завершение игры или голосование за остановку).
- Вся история игр, ответы и результаты теперь сохраняются и доступны для просмотра.
- Гибкий бонус за скорость: 20% от времени на вопрос.
- Можно настраивать время на ответ (1, 2, 3, 5 мин).
- Автоматический переход к следующему вопросу по таймеру.
- Улучшения в тексте напоминаний и окончания времени.
- Улучшения интерфейса, защита от случайных действий.
- Можно выбирать количество раундов, вопросов и уровень сложности.
- Защита от повторного запуска игры.
- Много мелких улучшений и исправлений.

Версия 1.4.x:
- Улучшения бонусов, индивидуального и командного режима.
- Улучшения регистрации, выбора капитана, рейтинга.

Версия 1.3.x:
- Таймеры, напоминания, бонусы за скорость.
- Улучшения генерации вопросов и проверки ответов.

Версия 1.2.x:
- Командный и индивидуальный режимы.
- Красивая регистрация, эмодзи, кнопки.

Версия 1.1.x:
- Поддержка OpenAI GPT-4o.
- Улучшения prompt и проверки ответов.

Версия 1.0.x:
- Первая рабочая версия квиз-бота.
'''

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'🤖 Квиз-бот\nТекущая версия: {VERSION}\n\nИзменения:\n{CHANGELOG}'
    )

# --- SQLite: инициализация базы и таблиц ---
# --- Возвращаю синхронные обёртки к db.py, теперь используем db.xxx без await ---

def get_questions_history(theme: str, limit: int = 50) -> list:
    return db.get_questions_history(theme, limit)

def add_question_to_history(theme: str, question: str):
    db.add_question_to_history(theme, question)

def get_last_game_id(chat_id):
    return db.get_last_game_id(chat_id)

def insert_answers(game_id, answers):
    db.insert_answers(game_id, answers)

def insert_game_participants(game_id, participants):
    db.insert_game_participants(game_id, participants)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
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
        await update.message.reply_text("Язык переключён на русский 🇷🇺")
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

def main_wrapper():
    print('DB INIT...')
    db.init_db()
    print('DB INIT DONE')
    print('Создаю Application...')
    app = ApplicationBuilder().token(TOKEN).build()
    print('Application создан')
    return app

async def main():
    app = main_wrapper()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('next', next_round_handler))
    # --- Новый хендлеры ---
    app.add_handler(CommandHandler('exit', exit_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('news', news_command))
    app.add_handler(CommandHandler('stat', stat_command))
    # --- Новый хендлер для выбора режима ---
    app.add_handler(CallbackQueryHandler(mode_callback, pattern='^mode_'))
    # --- Новый callback для выбора сложности ---
    app.add_handler(CallbackQueryHandler(difficulty_callback, pattern='^difficulty_'))
    # --- Новый callback для выбора количества раундов ---
    app.add_handler(CallbackQueryHandler(rounds_callback, pattern='^rounds_'))
    # --- Новый callback для выбора количества вопросов ---
    app.add_handler(CallbackQueryHandler(questions_callback, pattern='^questions_'))
    # --- Новый callback для выбора времени на вопрос ---
    app.add_handler(CallbackQueryHandler(time_callback, pattern='^time_'))
    # Используем кастомные фильтры для стадий
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & THEME_STAGE_FILTER, theme_handler))
    app.add_handler(CallbackQueryHandler(join_callback, pattern='^join$'))
    app.add_handler(CallbackQueryHandler(end_registration_callback, pattern='^end_registration$'))
    app.add_handler(CallbackQueryHandler(captain_callback, pattern='^captain_'))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern='^answer$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ANSWER_STAGE_FILTER, answer_message_handler))
    # --- Кнопки рейтинга и выхода ---
    app.add_handler(CallbackQueryHandler(show_rating_callback, pattern='^show_rating$'))
    app.add_handler(CallbackQueryHandler(leave_callback, pattern='^leave$'))
    # Универсальный CallbackQueryHandler для логирования любых callback_query
    async def log_any_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"[LOG] CallbackQuery: {update.callback_query.to_dict() if update.callback_query else update}")
        return False
    app.add_handler(CallbackQueryHandler(log_any_callback), group=100)
    # Логгеры — в самом конце!
    async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"[LOG] Incoming update: type={type(update)} content={update.to_dict()}")
        return False
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, log_all_updates), group=100)
    app.add_handler(CallbackQueryHandler(log_all_updates), group=100)
    app.add_handler(CommandHandler('lang', lang_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice_handler))
    print('Handlers добавлены, запускаю polling...')
    try:
        await app.run_polling()
    except RuntimeError as e:
        print('Polling error:', e)
        if "already running" in str(e) or "Cannot close a running event loop" in str(e):
            print("[ERROR] PTB не может закрыть event loop. Запуск в этом окружении невозможен. Используйте обычный Python или Jupyter/replit с поддержкой PTB 20+.")
            import sys
            sys.exit(1)
        else:
            raise
    print('Polling завершён')

print('=== BOT STARTED ===')
import sys
print('Python version:', sys.version)
try:
    with open('requirements.txt') as f:
        print('requirements.txt:', f.read())
except Exception as e:
    print('requirements.txt not found:', e)

print('Импортирую PTB...')
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
print('PTB импортирован')

print('Запуск main...')
import sys
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.run(main())
else:
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except RuntimeError as e:
        print('Loop error:', e)
        if "already running" in str(e) or "Cannot close a running event loop" in str(e):
            print("[ERROR] PTB не может закрыть event loop. Запуск в этом окружении невозможен. Используйте обычный Python или Jupyter/replit с поддержкой PTB 20+.")
            import sys
            sys.exit(1)
        else:
            raise
print('main завершён')

if __name__ == "__main__":
    import asyncio
    REPL_URL = f"https://{os.environ['REPL_SLUG']}.{os.environ['REPL_OWNER']}.repl.co"
    WEBHOOK_PATH = f"/{TOKEN}"
    WEBHOOK_URL = REPL_URL + WEBHOOK_PATH
    print(f"Webhook URL: {WEBHOOK_URL}")
    app = ApplicationBuilder().token(TOKEN).build()
    # ... add_handler ...
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
    async def log_any_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"[LOG] CallbackQuery: {update.callback_query.to_dict() if update.callback_query else update}")
        return False
    app.add_handler(CallbackQueryHandler(log_any_callback), group=100)
    async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"[LOG] Incoming update: type={type(update)} content={update.to_dict()}")
        return False
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, log_all_updates), group=100)
    app.add_handler(CallbackQueryHandler(log_all_updates), group=100)
    app.add_handler(CommandHandler('lang', lang_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice_handler))
    import db
    db.init_db()
    async def main():
        await app.bot.set_webhook(WEBHOOK_URL)
        print("Webhook set:", WEBHOOK_URL)
        await app.run_webhook(
            listen="0.0.0.0",
            port=443,  # Если не работает, попробуйте 80
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL,
        )
    asyncio.run(main())