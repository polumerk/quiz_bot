import json
import re
import aiohttp
import random
from typing import Any, Dict, List
from db import get_questions_history, add_question_to_history

START_PROMPT = 'Ты AI-ведущий интеллектуального квиза.'
GOOD_QUESTION_EXAMPLES = [
    'В каком году был основан Санкт-Петербург?',
    'Кто написал роман "Война и мир"?',
    'Как называется самая длинная река в России?',
    'Сколько планет в Солнечной системе?',
    'Какой элемент обозначается символом Fe?'
]
BAD_QUESTION_EXAMPLES = [
    'Как вы думаете, что важнее: счастье или успех?',
    'Почему небо голубое?',
    'Что вы чувствуете, когда идёте по лесу?',
    'Какой ваш любимый цвет?',
    'Что бы вы сделали, если бы выиграли миллион?'
]
FEEDBACK_GOOD = ['Молодец!', 'Отлично!', 'Супер!', 'Так держать!', 'Блестяще!']
FEEDBACK_BAD = ['Почти!', 'Не сдавайся!', 'В следующий раз получится!', 'Попробуй ещё!', 'Не унывай!']
SYSTEM_PROMPT_QUESTION = (
    "Ты — AI-ведущий интеллектуального квиза. "
    "Генерируй только однозначные вопросы с коротким, точным ответом. "
    "Не добавляй лишних пояснений, соблюдай формат строго."
)
SYSTEM_PROMPT_CHECK = (
    "Ты — AI-ведущий квиза, оцениваешь ответы по смыслу. "
    "Не допускай субъективности."
)

async def openai_generate_questions(theme: str, round_num: int, chat_id: int, get_difficulty, get_questions_per_round) -> List[Any]:
    with open('openai_key.txt', 'r', encoding='utf-8') as f:
        OPENAI_KEY = f.read().strip()
    history_questions = get_questions_history(theme, limit=50)
    history_text = ''
    if history_questions:
        history_text = '\nВот примеры вопросов, которые уже были ранее, не повторяй их:\n' + '\n'.join(f'- {q}' for q in history_questions)
    difficulty = get_difficulty(chat_id)
    questions_per_round = get_questions_per_round(chat_id)
    prompt = build_openai_prompt(theme, round_num, questions_per_round, history_text, difficulty)
    temperature = 0.2
    headers = {
        'Authorization': f'Bearer {OPENAI_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": temperature
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
            result = await resp.json()
            try:
                text = result['choices'][0]['message']['content']
                text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
                text = text.strip()
                questions = json.loads(text)
                unique_questions = []
                history_set = set(q.strip().lower() for q in history_questions)
                for q in questions:
                    q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
                    if q_text.strip().lower() not in history_set:
                        unique_questions.append(q)
                attempts = 0
                while len(unique_questions) < questions_per_round and attempts < 2:
                    missing = questions_per_round - len(unique_questions)
                    extra_prompt = build_openai_prompt(theme, round_num, missing, history_text, difficulty)
                    data["messages"][1]["content"] = extra_prompt
                    async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp2:
                        result2 = await resp2.json()
                        try:
                            text2 = result2['choices'][0]['message']['content']
                            text2 = re.sub(r'^```json\s*|```$', '', text2.strip(), flags=re.MULTILINE)
                            text2 = text2.strip()
                            new_questions = json.loads(text2)
                            for q in new_questions:
                                q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
                                if q_text.strip().lower() not in history_set:
                                    unique_questions.append(q)
                                    history_set.add(q_text.strip().lower())
                        except Exception as e:
                            print('[LOG] Ошибка парсинга OpenAI (доп. попытка):', e)
                    attempts += 1
                for q in unique_questions:
                    q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
                    add_question_to_history(theme, q_text)
                return unique_questions
            except Exception as e:
                print('[LOG] Ошибка парсинга OpenAI:', e)
                return ["Ошибка генерации вопросов. Попробуйте ещё раз."]

def build_openai_prompt(theme: str, round_num: int, questions_per_round: int, history_text: str, difficulty: str = 'medium') -> str:
    return (
        START_PROMPT +
        f"\nТема: {theme}\nСгенерируй {questions_per_round} уникальных, интересных и однозначных вопросов для раунда {round_num}. "
        f"Все вопросы должны быть строго уровня сложности: {difficulty}. "
        "Каждый вопрос должен иметь только один короткий, точный и однозначный правильный ответ (answer). "
        "Избегай размытых, субъективных, философских или дискуссионных вопросов. Не задавай вопросы с множеством возможных вариантов ответа. "
        "Формат ответа: JSON-массив объектов с полями: question, answer, difficulty (easy/medium/hard). "
        "Верни только JSON-массив, без обёртки и лишнего текста. "
        f"{history_text}"
    )

async def openai_check_answers(theme: str, questions: List[str], answers: List[str]) -> List[Dict[str, Any]]:
    prompt = (
        START_PROMPT +
        f"\nТема: {theme}\nВот вопросы и ответы участников (формат JSON: список объектов с 'question' и 'answer'). "
        "Проверь ответы по смыслу, оцени каждый как 'правильно' или 'неправильно', дай короткое объяснение. "
        "Верни только JSON-массив объектов: question, answer, correct (true/false), explanation, correct_answer. "
        "Без обёртки, без дополнительных ключей, без текста до и после массива."
    )
    qa_pairs = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
    with open('openai_key.txt', 'r', encoding='utf-8') as f:
        OPENAI_KEY = f.read().strip()
    headers = {
        'Authorization': f'Bearer {OPENAI_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_CHECK},
            {"role": "user", "content": prompt + "\n" + json.dumps(qa_pairs, ensure_ascii=False)}
        ],
        "max_tokens": 2048,
        "temperature": 0.2
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
            result = await resp.json()
            try:
                text = result['choices'][0]['message']['content']
                text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
                text = text.strip()
                parsed = json.loads(text)
                if isinstance(parsed, list) and all(isinstance(r, dict) for r in parsed):
                    return parsed
                else:
                    print('[LOG] Ошибка: OpenAI вернул не список словарей:', parsed)
                    return []
            except Exception as e:
                print('[LOG] Ошибка парсинга OpenAI:', e, result)
                return [] 