import json
import re
import aiohttp
import random
import os
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
# Feedback константы удалены, так как не используются в текущей версии
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
    # Try to get OpenAI key from environment variable first, then from file (for backward compatibility)
    OPENAI_KEY = os.getenv('OPENAI_API_KEY')
    
    if not OPENAI_KEY:
        # Fallback to file (for backward compatibility)
        try:
            with open('openai_key.txt', 'r', encoding='utf-8') as f:
                OPENAI_KEY = f.read().strip()
        except FileNotFoundError:
            print('[LOG] OpenAI API key not found in environment variable OPENAI_API_KEY or openai_key.txt file')
            return [{"question": "❌ OpenAI API ключ не настроен. Добавьте переменную OPENAI_API_KEY в Replit Secrets", "answer": "N/A", "difficulty": "medium"}]
    
    if not OPENAI_KEY or not OPENAI_KEY.startswith('sk-'):
        print('[LOG] Invalid OpenAI API key')
        return [{"question": "❌ Неверный OpenAI API ключ. Проверьте переменную OPENAI_API_KEY", "answer": "N/A", "difficulty": "medium"}]
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
            # Handle non-200 status codes
            if resp.status != 200:
                error_text = await resp.text()
                print(f'[LOG] OpenAI HTTP Error {resp.status}: {error_text}')
                return [{"question": f"Ошибка OpenAI API (HTTP {resp.status})", "answer": "N/A", "difficulty": "medium"}]
            
            try:
                result = await resp.json()
            except Exception as e:
                response_text = await resp.text()
                print(f'[LOG] Failed to parse OpenAI response as JSON: {e}')
                return [{"question": "Ошибка парсинга ответа OpenAI", "answer": "N/A", "difficulty": "medium"}]
            
            # Check if OpenAI returned an error
            if not isinstance(result, dict):
                print('[LOG] OpenAI response is not a dict:', result)
                return [{"question": "Ошибка генерации вопросов. Попробуйте ещё раз.", "answer": "N/A", "difficulty": "medium"}]
            
            if 'error' in result:
                print('[LOG] OpenAI API Error:', result['error'])
                return [{"question": f"Ошибка OpenAI: {result['error'].get('message', 'Unknown error')}", "answer": "N/A", "difficulty": "medium"}]
            
            if 'choices' not in result or not result['choices']:
                print('[LOG] OpenAI response missing choices:', result)
                return [{"question": "Ошибка генерации вопросов. Попробуйте ещё раз.", "answer": "N/A", "difficulty": "medium"}]
            
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
                        
                        # Check second request too
                        if isinstance(result2, dict) and 'choices' in result2 and result2['choices']:
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
                        else:
                            print('[LOG] Ошибка второго запроса к OpenAI:', result2)
                    attempts += 1
                for q in unique_questions:
                    q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
                    add_question_to_history(theme, q_text)
                return unique_questions if unique_questions else [{"question": "Ошибка генерации вопросов. Попробуйте ещё раз.", "answer": "N/A", "difficulty": "medium"}]
            except Exception as e:
                print('[LOG] Ошибка парсинга OpenAI:', e)
                return [{"question": "Ошибка генерации вопросов. Попробуйте ещё раз.", "answer": "N/A", "difficulty": "medium"}]

def build_openai_prompt(theme: str, round_num: int, questions_per_round: int, history_text: str, difficulty: str = 'medium') -> str:
    # АДАПТИВНАЯ СИСТЕМА ФОРМИРОВАНИЯ ПРОМПТОВ
    
    # 1. ОПРЕДЕЛЕНИЯ УРОВНЕЙ СЛОЖНОСТИ С КОНКРЕТНЫМИ КРИТЕРИЯМИ
    difficulty_definitions = {
        'easy': {
            'description': 'ЛЕГКИЙ уровень - общеизвестные факты, школьная программа, популярные знания',
            'criteria': 'Должен знать каждый школьник или человек с базовым образованием',
            'examples': [
                'Столица России?',
                'Сколько дней в году?',
                'В каком городе находится Красная площадь?',
                'Самый большой океан на Земле?'
            ],
            'avoid': 'специализированные термины, редкие даты, профессиональные знания'
        },
        'medium': {
            'description': 'СРЕДНИЙ уровень - требует образования, культурные знания, исторические факты',
            'criteria': 'Требует среднего образования, эрудиции, общих культурных знаний',
            'examples': [
                'В каком году был основан Санкт-Петербург?',
                'Кто написал роман "Война и мир"?',
                'Какой элемент обозначается символом Fe?',
                'Кто командовал русским флотом в Чесменском сражении?'
            ],
            'avoid': 'слишком узкоспециализированные области, очень редкие факты'
        },
        'hard': {
            'description': 'СЛОЖНЫЙ уровень - глубокие знания, специализированная информация, детали',
            'criteria': 'Требует глубоких знаний, специализации, изучения деталей',
            'examples': [
                'В каком году был принят Ништадтский мир?',
                'Кто был архитектором Исаакиевского собора?',
                'Какой изотоп урана используется в ядерных реакторах?',
                'Кто был наставником Александра Македонского?'
            ],
            'avoid': 'слишком общие или базовые вопросы'
        }
    }
    
    # 2. СТРАТЕГИИ ДЛЯ РАЗНОГО КОЛИЧЕСТВА ВОПРОСОВ
    if questions_per_round <= 3:
        quantity_strategy = """
СТРАТЕГИЯ ДЛЯ МАЛОГО КОЛИЧЕСТВА ВОПРОСОВ (1-3):
- Выбирай САМЫЕ КАЧЕСТВЕННЫЕ и показательные вопросы по теме
- Каждый вопрос должен быть ИДЕАЛЬНЫМ примером уровня сложности
- Максимальное разнообразие аспектов темы
- Фокусируйся на самых важных и интересных деталях"""
    elif questions_per_round <= 7:
        quantity_strategy = """
СТРАТЕГИЯ ДЛЯ СРЕДНЕГО КОЛИЧЕСТВА ВОПРОСОВ (4-7):
- Покрывай основные аспекты и подтемы
- Сбалансируй между базовыми и более специфичными вопросами
- Поддерживай разнообразие и динамику
- Включай как исторические, так и фактологические элементы"""
    else:
        quantity_strategy = """
СТРАТЕГИЯ ДЛЯ БОЛЬШОГО КОЛИЧЕСТВА ВОПРОСОВ (8+):
- Обеспечь широкое и глубокое покрытие всей темы
- Включай вопросы разной специфичности и направленности
- Создавай логическую прогрессию и разнообразие
- Избегай повторения схожих формулировок и подходов"""
    
    # 3. СПЕЦИАЛИЗАЦИЯ ПО ТЕМАМ
    theme_guidance = ""
    theme_lower = theme.lower()
    
    if any(word in theme_lower for word in ['спорт', 'футбол', 'олимпиада', 'игра']):
        theme_guidance = """
СПЕЦИАЛЬНО ДЛЯ СПОРТИВНОЙ ТЕМЫ:
- Конкретные цифры (количество игроков, очки, время игры)
- Исторические спортивные факты (годы проведения, места)
- Правила и спортивные термины (но избегай спорные трактовки)
- Рекорды и достижения с точными данными"""
    
    elif any(word in theme_lower for word in ['история', 'исторический', 'война', 'царь']):
        theme_guidance = """
СПЕЦИАЛЬНО ДЛЯ ИСТОРИЧЕСКОЙ ТЕМЫ:
- Точные даты важных событий и периодов
- Имена исторических личностей и их роли
- Географические названия и их историческое значение
- Причинно-следственные связи событий"""
    
    elif any(word in theme_lower for word in ['наука', 'физика', 'химия', 'биология', 'математика']):
        theme_guidance = """
СПЕЦИАЛЬНО ДЛЯ НАУЧНОЙ ТЕМЫ:
- Научные формулы, символы и обозначения
- Имена ученых и их открытия
- Точные определения научных терминов
- Законы и принципы с их авторами"""
    
    elif any(word in theme_lower for word in ['география', 'страна', 'город', 'река']):
        theme_guidance = """
СПЕЦИАЛЬНО ДЛЯ ГЕОГРАФИЧЕСКОЙ ТЕМЫ:
- Точные названия стран, городов, рек, гор
- Численные данные (площадь, население, высота)
- Столицы и административные центры
- Географические особенности и рекорды"""
    
    # 4. ПОЛУЧЕНИЕ НАСТРОЕК ДЛЯ ТЕКУЩЕГО УРОВНЯ
    current_difficulty = difficulty_definitions.get(difficulty, difficulty_definitions['medium'])
    
    # 5. ФОРМИРОВАНИЕ ПРИМЕРОВ ПО УРОВНЮ
    level_examples = "\n".join(f'- "{q}"' for q in current_difficulty['examples'])
    
    # 6. ОБЩИЕ КАЧЕСТВЕННЫЕ ПРИМЕРЫ (ИЗБЕГАТЬ)
    general_bad = "\n".join(f'- "{q}"' for q in BAD_QUESTION_EXAMPLES)
    
    # 7. ФОРМИРОВАНИЕ ИТОГОВОГО АДАПТИВНОГО ПРОМПТА
    return f"""{START_PROMPT}

ЗАДАЧА: Сгенерируй {questions_per_round} вопросов для темы "{theme}" (раунд {round_num})

УРОВЕНЬ СЛОЖНОСТИ: {difficulty.upper()}
{current_difficulty['description']}
Критерий отбора: {current_difficulty['criteria']}

ПРИМЕРЫ ВОПРОСОВ УРОВНЯ {difficulty.upper()}:
{level_examples}

{quantity_strategy}

{theme_guidance}

ОБЩИЕ ТРЕБОВАНИЯ:
- Каждый вопрос должен иметь ЕДИНСТВЕННЫЙ правильный ответ
- Формулируй максимально конкретно и недвусмысленно
- Строго соблюдай уровень сложности {difficulty}
- Избегай: {current_difficulty['avoid']}

НИКОГДА НЕ ЗАДАВАЙ СУБЪЕКТИВНЫЕ ВОПРОСЫ ТИПА:
{general_bad}

ФОРМАТ ОТВЕТА: JSON-массив объектов с полями: question, answer, difficulty
Верни ТОЛЬКО JSON-массив, без обёртки и лишнего текста.

{history_text}"""

async def openai_check_answers(theme: str, questions: List[str], answers: List[str]) -> List[Dict[str, Any]]:
    prompt = (
        START_PROMPT +
        f"\nТема: {theme}\nВот вопросы и ответы участников (формат JSON: список объектов с 'question' и 'answer'). "
        "Проверь ответы по смыслу, оцени каждый как 'правильно' или 'неправильно', дай короткое объяснение. "
        "Верни только JSON-массив объектов: question, answer, correct (true/false), explanation, correct_answer. "
        "Без обёртки, без дополнительных ключей, без текста до и после массива."
    )
    qa_pairs = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
    
    # Get OpenAI key from environment variable or file
    OPENAI_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_KEY:
        try:
            with open('openai_key.txt', 'r', encoding='utf-8') as f:
                OPENAI_KEY = f.read().strip()
        except FileNotFoundError:
            print('[LOG] OpenAI API key not found for check_answers')
            return []
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
            
            # Check if OpenAI returned an error
            if not isinstance(result, dict):
                print('[LOG] OpenAI response is not a dict:', result)
                return []
            
            if 'error' in result:
                print('[LOG] OpenAI API Error:', result['error'])
                return []
            
            if 'choices' not in result or not result['choices']:
                print('[LOG] OpenAI response missing choices:', result)
                return []
            
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