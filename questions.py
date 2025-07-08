import json
import re
import aiohttp
import random
import os
from typing import Any, Dict, List
from db import get_questions_history, add_question_to_history
from src.ai.intelligent_prompts import IntelligentPrompts
from src.models.types import QuestionType, Difficulty

START_PROMPT = 'Ты AI-ведущий интеллектуального квиза в стиле "Квиз, плиз!"'

# Примеры интеллектуальных вопросов в стиле профессиональных квизов
INTELLECTUAL_EXAMPLES = [
    {
        "question": "В США в XIX веке беглые рабы совершали одно преступление уже самим фактом побега. Но их дискриминировали еще и второе — воровство. Что это за правонарушение?",
        "answer": "Побег (они воровали себя у рабовладельца)",
        "type": "исторический с подвохом"
    },
    {
        "question": "Изначально гривну рубили специальные менялы прямо на скамьях на рынке. Какое финансовое учреждение появилось на основе этого процесса?",
        "answer": "Банк (от нем. Bank — скамья)",
        "type": "этимологический"
    },
    {
        "question": "В 1947 году в газетах появилось сообщение о смерти греческого короля Георга II. Однако многие в течение нескольких дней не верили в то, что он действительно умер. Назовите дату смерти короля.",
        "answer": "1 апреля",
        "type": "с подсказкой в тексте"
    }
]

# Плохие примеры простых вопросов
BAD_QUESTION_EXAMPLES = [
    'Столица Франции?',
    'Кто написал "Войну и мир"?',
    'Сколько планет в Солнечной системе?',
    'Какой цвет получится при смешивании красного и синего?'
]

FEEDBACK_GOOD = ['Молодец!', 'Отлично!', 'Супер!', 'Так держать!', 'Блестяще!', 'Браво!', 'Великолепно!']
FEEDBACK_BAD = ['Почти!', 'Не сдавайся!', 'В следующий раз получится!', 'Попробуй ещё!', 'Не унывай!', 'Близко к истине!']

SYSTEM_PROMPT_QUESTION = (
    "Ты — AI-ведущий интеллектуального квиза в стиле 'Квиз, плиз!'. "
    "Создавай ИНТЕЛЛЕКТУАЛЬНЫЕ вопросы, которые:\n"
    "1. Провоцируют размышления, а не просто проверяют память\n"
    "2. Содержат элемент неожиданности или подвоха\n"
    "3. Многослойные - с подсказками в самом тексте\n"
    "4. Учитывают культурный контекст русскоязычной аудитории\n"
    "5. Имеют точный, однозначный ответ\n"
    "Избегай банальных вопросов типа 'Столица Франции?'"
)

SYSTEM_PROMPT_CHECK = (
    "Ты — AI-ведущий квиза, оцениваешь ответы по смыслу. "
    "Учитывай возможные варианты написания и синонимы. "
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
    prompt = build_enhanced_openai_prompt(theme, round_num, questions_per_round, history_text, difficulty)
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
                    extra_prompt = build_enhanced_openai_prompt(theme, round_num, missing, history_text, difficulty)
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
    
    # Примеры интеллектуальных вопросов по темам
    theme_examples = get_theme_examples(theme, difficulty)
    
    # Инструкции по уровню сложности
    difficulty_instructions = get_difficulty_instructions(difficulty)
    
    return (
        START_PROMPT +
        f"\n\n🎯 ЗАДАЧА: Создай {questions_per_round} ИНТЕЛЛЕКТУАЛЬНЫХ вопросов для темы '{theme}' (раунд {round_num})\n"
        f"📊 УРОВЕНЬ СЛОЖНОСТИ: {difficulty}\n\n"
        
        "🧠 ПРИНЦИПЫ СОЗДАНИЯ ИНТЕЛЛЕКТУАЛЬНЫХ ВОПРОСОВ:\n"
        "1. 🎪 ПРОВОЦИРУЙ РАЗМЫШЛЕНИЯ - не просто проверяй память\n"
        "2. 🎭 ДОБАВЛЯЙ ЭЛЕМЕНТ НЕОЖИДАННОСТИ или подвоха\n"
        "3. 🧩 ДЕЛАЙ МНОГОСЛОЙНЫМИ - с подсказками в самом тексте\n"
        "4. 🇷🇺 УЧИТЫВАЙ русскоязычную культуру и реалии\n"
        "5. ✅ ОБЕСПЕЧЬ точный, однозначный ответ\n\n"
        
        f"📚 ПРИМЕРЫ ХОРОШИХ ИНТЕЛЛЕКТУАЛЬНЫХ ВОПРОСОВ:\n{theme_examples}\n\n"
        
        "❌ ИЗБЕГАЙ БАНАЛЬНЫХ ВОПРОСОВ типа:\n"
        "- 'Столица Франции?' (слишком просто)\n"
        "- 'Кто написал Войну и мир?' (проверка памяти)\n"
        "- 'Сколько планет в Солнечной системе?' (школьная программа)\n\n"
        
        f"🎯 ТРЕБОВАНИЯ К СЛОЖНОСТИ ({difficulty}):\n{difficulty_instructions}\n\n"
        
        "📝 ФОРМАТ ОТВЕТА: JSON-массив объектов с полями:\n"
        "- question: текст вопроса\n"
        "- answer: точный ответ\n"
        "- difficulty: уровень сложности\n\n"
        
        "⚠️ ВАЖНО: Верни ТОЛЬКО JSON-массив, без обёртки и лишнего текста!\n"
        f"{history_text}"
    )

def get_theme_examples(theme: str, difficulty: str) -> str:
    """Возвращает примеры интеллектуальных вопросов для конкретной темы"""
    
    theme_lower = theme.lower()
    
    if "истор" in theme_lower:
        return """
🏛️ ИСТОРИЯ:
- "В средневековой Европе существовала профессия 'будильник'. Как таких людей называли и что они делали?"
  → "Knocker-up (или стукач) - будили людей, стуча в окна палкой"
- "Почему в древнем Риме соль была настолько ценной, что ей платили жалованье солдатам?"
  → "Отсюда произошло слово 'salary' (зарплата) от латинского 'salarium'"
- "В 1912 году капитан Скотт нашёл в Антарктиде палатку с запиской. Что там было написано?"
  → "Амундсен опередил их на 34 дня - записка о достижении Южного полюса"
"""
    
    elif "кино" in theme_lower or "фильм" in theme_lower:
        return """
🎬 КИНО:
- "В этом фильме герой говорит: 'Я не сумасшедший, моя реальность просто отличается от вашей'. Назовите фильм."
  → "Алиса в стране чудес (2010, Тим Бертон)"
- "Режиссёр специально снимал актёров в хронологическом порядке, чтобы показать реальную деградацию. Какой это фильм?"
  → "Реквием по мечте"
- "В каком фильме актёр действительно порезал руку, но продолжил играть сцену?"
  → "Джанго освобождённый (Леонардо Ди Каприо)"
"""
    
    elif "спорт" in theme_lower:
        return """
⚽ СПОРТ:
- "Почему в теннисе счёт идёт 15-30-40, а не 15-30-45?"
  → "От французского 'quarante' (сорок), которое звучало как 'quarante-cinq'"
- "Этот вид спорта был исключён из Олимпиады после того, как зрители начали подкупать судей. Что это?"
  → "Перетягивание каната"
- "В каком виде спорта запрещено играть левой рукой?"
  → "Поло"
"""
    
    elif "наука" in theme_lower or "физика" in theme_lower or "химия" in theme_lower:
        return """
🔬 НАУКА:
- "Почему в космосе нельзя плакать?"
  → "Слёзы не стекают из-за отсутствия гравитации, образуя пузыри"
- "Этот элемент назван в честь планеты, которая ещё не была открыта. Что это?"
  → "Уран (элемент уран открыт в 1789, планета - в 1781)"
- "Какой орган человека продолжает расти всю жизнь?"
  → "Нос и уши (хрящевая ткань)"
"""
    
    elif "география" in theme_lower:
        return """
🌍 ГЕОГРАФИЯ:
- "Эта страна имеет квадратную форму, но её столица находится не в центре. Почему?"
  → "Колорадо (США) - столица Денвер смещена из-за гор"
- "В какой стране есть город, где запрещено умирать?"
  → "Норвегия, Лонгйир (тела не разлагаются в вечной мерзлоте)"
- "Почему Гренландия называется 'Зелёной землёй', хотя покрыта льдом?"
  → "Эрик Рыжий назвал так для привлечения поселенцев"
"""
    
    elif "музыка" in theme_lower:
        return """
🎵 МУЗЫКА:
- "Эта песня была написана как протест против войны, но стала гимном патриотов. Какая?"
  → "Born in the USA (Брюс Спрингстин)"
- "Почему в оркестре скрипачи двигают смычками в разные стороны?"
  → "Чтобы избежать визуального хаоса и создать единообразие"
- "Какой инструмент изобрели, чтобы заменить целый оркестр?"
  → "Орган"
"""
    
    else:
        return """
🧠 ОБЩИЕ ЗНАНИЯ:
- "Что общего между зеброй и штрих-кодом?"
  → "Оба используют чёрно-белые полосы для идентификации"
- "Почему в лифтах есть зеркала?"
  → "Чтобы люди не скучали в ожидании и не замечали времени"
- "Какое изобретение появилось раньше: зажигалка или спички?"
  → "Зажигалка (1823 vs 1826)"
"""

def get_difficulty_instructions(difficulty: str) -> str:
    """Возвращает инструкции для конкретного уровня сложности"""
    
    if difficulty == "easy":
        return """
🟢 ЛЁГКИЙ УРОВЕНЬ:
- Вопросы должны быть доступны широкой аудитории
- Можно использовать общеизвестные факты, но с интересной подачей
- Подсказки в тексте должны быть достаточно очевидными
- Ответ должен быть логически выводимым
"""
    
    elif difficulty == "hard":
        return """
🔴 СЛОЖНЫЙ УРОВЕНЬ:
- Требуй глубоких знаний или нестандартного мышления
- Подсказки могут быть завуалированными
- Можно использовать специализированные знания
- Элемент неожиданности должен быть ярко выражен
"""
    
    else:  # medium
                 return """
🟡 СРЕДНИЙ УРОВЕНЬ:
- Баланс между доступностью и сложностью
- Подсказки должны помочь внимательному игроку
- Требуй размышлений, но не узкоспециальных знаний
- Ответ должен быть "Ага! Точно!" момент
"""

def select_question_types(theme: str, difficulty: Difficulty, questions_count: int) -> List[QuestionType]:
    """Выбрать типы вопросов на основе темы и сложности"""
    
    # Базовые типы для разных тем
    theme_lower = theme.lower()
    
    if "истор" in theme_lower:
        base_types = [QuestionType.HISTORICAL_TWIST, QuestionType.ETYMOLOGY, QuestionType.HIDDEN_CLUE]
    elif "кино" in theme_lower or "фильм" in theme_lower:
        base_types = [QuestionType.CULTURAL_REFERENCE, QuestionType.HIDDEN_CLUE, QuestionType.UNEXPECTED_ANSWER]
    elif "спорт" in theme_lower:
        base_types = [QuestionType.LOGIC_PUZZLE, QuestionType.ETYMOLOGY, QuestionType.UNEXPECTED_ANSWER]
    elif "наука" in theme_lower:
        base_types = [QuestionType.LOGIC_PUZZLE, QuestionType.RIDDLE, QuestionType.UNEXPECTED_ANSWER]
    else:
        base_types = [QuestionType.RIDDLE, QuestionType.LOGIC_PUZZLE, QuestionType.UNEXPECTED_ANSWER]
    
    # Добавляем типы в зависимости от сложности
    if difficulty == Difficulty.EASY:
        base_types.append(QuestionType.STANDARD)
        base_types.append(QuestionType.CULTURAL_REFERENCE)
    elif difficulty == Difficulty.HARD:
        base_types.extend([QuestionType.ETYMOLOGY, QuestionType.HIDDEN_CLUE])
    
    # Распределяем типы по количеству вопросов
    selected_types = []
    for i in range(questions_count):
        selected_types.append(base_types[i % len(base_types)])
    
    return selected_types

def build_enhanced_openai_prompt(theme: str, round_num: int, questions_per_round: int, 
                                history_text: str, difficulty: str = 'medium') -> str:
    """Построить улучшенный промпт с использованием интеллектуальных типов"""
    
    # Конвертируем строковую сложность в enum
    try:
        difficulty_enum = Difficulty(difficulty)
    except ValueError:
        difficulty_enum = Difficulty.MEDIUM
    
    # Выбираем типы вопросов
    question_types = select_question_types(theme, difficulty_enum, questions_per_round)
    
    # Создаем промпт с микшированием типов
    mixed_prompt = f"""
🎯 ЗАДАЧА: Создай {questions_per_round} ИНТЕЛЛЕКТУАЛЬНЫХ вопросов для темы '{theme}' (раунд {round_num})
📊 УРОВЕНЬ СЛОЖНОСТИ: {difficulty}

🧠 ПРИНЦИПЫ СОЗДАНИЯ ИНТЕЛЛЕКТУАЛЬНЫХ ВОПРОСОВ:
1. 🎪 ПРОВОЦИРУЙ РАЗМЫШЛЕНИЯ - не просто проверяй память
2. 🎭 ДОБАВЛЯЙ ЭЛЕМЕНТ НЕОЖИДАННОСТИ или подвоха
3. 🧩 ДЕЛАЙ МНОГОСЛОЙНЫМИ - с подсказками в самом тексте
4. 🇷🇺 УЧИТЫВАЙ русскоязычную культуру и реалии
5. ✅ ОБЕСПЕЧЬ точный, однозначный ответ

📚 ТИПЫ ВОПРОСОВ ДЛЯ ГЕНЕРАЦИИ:
{_format_question_types_for_prompt(question_types)}

{get_theme_examples(theme, difficulty)}

❌ ИЗБЕГАЙ БАНАЛЬНЫХ ВОПРОСОВ типа:
- 'Столица Франции?' (слишком просто)
- 'Кто написал Войну и мир?' (проверка памяти)
- 'Сколько планет в Солнечной системе?' (школьная программа)

{get_difficulty_instructions(difficulty)}

📝 ФОРМАТ ОТВЕТА: JSON-массив объектов с полями:
- question: текст вопроса
- answer: точный ответ
- difficulty: уровень сложности
- question_type: тип вопроса
- explanation: объяснение ответа (опционально)

⚠️ ВАЖНО: Верни ТОЛЬКО JSON-массив, без обёртки и лишнего текста!
{history_text}
"""
    
    return mixed_prompt

def _format_question_types_for_prompt(question_types: List[QuestionType]) -> str:
    """Форматировать типы вопросов для промпта"""
    
    type_descriptions = {
        QuestionType.STANDARD: "Стандартный интеллектуальный вопрос",
        QuestionType.RIDDLE: "Загадка с подвохом",
        QuestionType.ETYMOLOGY: "Этимологический вопрос",
        QuestionType.HISTORICAL_TWIST: "Исторический с поворотом",
        QuestionType.LOGIC_PUZZLE: "Логическая головоломка",
        QuestionType.CULTURAL_REFERENCE: "Культурная отсылка",
        QuestionType.HIDDEN_CLUE: "Подсказка скрыта в тексте",
        QuestionType.UNEXPECTED_ANSWER: "Неожиданный ответ"
    }
    
    formatted = []
    for i, qtype in enumerate(question_types, 1):
        formatted.append(f"{i}. {type_descriptions.get(qtype, 'Интеллектуальный вопрос')} ({qtype.value})")
    
    return "\n".join(formatted)

async def openai_check_answers(theme: str, questions: List[str], answers: List[str]) -> List[Dict[str, Any]]:
    prompt = (
        START_PROMPT +
        f"\n\n🎯 ЗАДАЧА: Проверь ответы участников квиза по теме '{theme}'\n\n"
        
        "🧠 ПРИНЦИПЫ ПРОВЕРКИ ИНТЕЛЛЕКТУАЛЬНЫХ ОТВЕТОВ:\n"
        "1. 🎪 ОЦЕНИВАЙ ПО СМЫСЛУ, а не по точному совпадению\n"
        "2. 🎭 УЧИТЫВАЙ синонимы, сокращения, разные формулировки\n"
        "3. 🧩 ПРИНИМАЙ частично правильные ответы, если суть верна\n"
        "4. 🇷🇺 УЧИТЫВАЙ русскоязычные особенности (ё/е, разные падежи)\n"
        "5. ✅ БУДЬ СПРАВЕДЛИВЫМ - если человек понял суть, засчитывай\n\n"
        
        "📝 ПРИМЕРЫ ГИБКОЙ ПРОВЕРКИ:\n"
        "- Вопрос: 'Столица Франции?' → Правильно: 'Париж', 'Paris', 'париж'\n"
        "- Вопрос: 'Автор Войны и мира?' → Правильно: 'Толстой', 'Л.Н.Толстой', 'Лев Толстой'\n"
        "- Вопрос: 'Сколько планет?' → Правильно: '8', 'восемь', 'восемь планет'\n\n"
        
        "⚠️ ФОРМАТ ОТВЕТА: JSON-массив объектов с полями:\n"
        "- question: исходный вопрос\n"
        "- answer: ответ участника\n"
        "- correct: true/false\n"
        "- explanation: краткое объяснение оценки\n"
        "- correct_answer: правильный ответ\n\n"
        
        "📊 ДАННЫЕ ДЛЯ ПРОВЕРКИ (JSON список пар вопрос-ответ):\n"
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