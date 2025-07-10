# 🔧 Детальные шаги формирования вопросов Quiz Bot 2.0

## 📋 Обзор процесса

Формирование вопросов в Quiz Bot 2.0 - это сложный многоэтапный процесс, включающий валидацию, генерацию через OpenAI, проверку дублирования, парсинг и сохранение результатов.

## 🚀 Полный цикл формирования вопросов

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        QUESTION GENERATION PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [1] ИНИЦИАЦИЯ      [2] ВАЛИДАЦИЯ     [3] ИСТОРИЯ        [4] ПРОМПТ         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ start_round │───▶│ Настройки   │───▶│ Получение   │───▶│ Построение  │   │
│  │             │    │ игры        │    │ истории     │    │ запроса     │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                             │
│  [5] ЗАПРОС         [6] ОБРАБОТКА     [7] ВАЛИДАЦИЯ     [8] СОХРАНЕНИЕ     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ OpenAI API  │───▶│ Парсинг     │───▶│ Проверка    │───▶│ В игровое   │   │
│  │             │    │ JSON        │    │ качества    │    │ состояние   │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                             │
│  [9] ДУБЛИРОВАНИЕ   [10] ГОТОВНОСТЬ   [11] ЗАПУСК       [12] ОБРАБОТКА     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ Проверка    │───▶│ Проверка    │───▶│ Показ       │───▶│ Ошибки и    │   │
│  │ дублей      │    │ готовности  │    │ вопросов    │    │ фолбэки     │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔍 Детальный анализ каждого шага

### **ШАГ 1: Инициация процесса**

**Файл:** `src/game/logic.py` → `start_round()`

```python
async def start_round(context: ContextTypes.DEFAULT_TYPE, chat_id: ChatID) -> None:
    """Start a new round of the game"""
    game_state = get_game_state(chat_id)
    
    # 1.1 Проверка наличия настроек
    if not game_state.settings:
        await context.bot.send_message(
            chat_id, 
            "❌ Ошибка: настройки игры не заданы. Используйте /start для настройки."
        )
        return
    
    settings = game_state.settings
    
    # 1.2 Уведомление пользователя о начале генерации
    await context.bot.send_message(chat_id, "🧠 Генерирую вопросы...")
```

**Логика проверок:**
- ✅ Существует ли игровое состояние?
- ✅ Есть ли настройки игры?
- ✅ Все ли обязательные поля заполнены?

### **ШАГ 2: Валидация настроек**

**Извлечение параметров:**
```python
# 2.1 Получение параметров из настроек
theme = settings.theme              # "История России"
difficulty = settings.difficulty    # Difficulty.MEDIUM
rounds = settings.rounds            # 2
questions_per_round = settings.questions_per_round  # 5
time_per_question = settings.time_per_question      # 300
```

**Проверки валидности:**
```python
# 2.2 Внутренние проверки (неявные)
if not theme or len(theme) < 2:
    # Ошибка: тема слишком короткая
    
if questions_per_round < 1 or questions_per_round > 20:
    # Ошибка: некорректное количество вопросов
    
if difficulty not in [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]:
    # Ошибка: неизвестная сложность
```

### **ШАГ 3: Получение истории вопросов**

**Файл:** `questions.py` → `openai_generate_questions()`

```python
# 3.1 Запрос к базе данных
history_questions = get_questions_history(theme, limit=50)

# 3.2 Формирование текста истории
history_text = ''
if history_questions:
    history_text = ('\nВот примеры вопросов, которые уже были ранее, '
                   'не повторяй их:\n' + 
                   '\n'.join(f'- {q}' for q in history_questions))
```

**Логика работы с историей:**
- 📊 Получаем последние 50 вопросов по теме
- 🔍 Формируем список для избежания дублирования
- 📝 Включаем в промпт для OpenAI

**Пример history_text:**
```
Вот примеры вопросов, которые уже были ранее, не повторяй их:
- В каком году была Куликовская битва?
- Кто был первым царем из династии Романовых?
- В каком году была основана Москва?
```

### **ШАГ 4: Построение промпта**

**Файл:** `questions.py` → `build_openai_prompt()`

```python
def build_openai_prompt(theme: str, round_num: int, questions_per_round: int, 
                       history_text: str, difficulty: str = 'medium') -> str:
    
    # 4.1 Специальные примеры для спорта
    sport_examples = ""
    if "спорт" in theme.lower():
        sport_examples = """
ПРИМЕРЫ ХОРОШИХ спортивных вопросов с точными ответами:
- "Сколько игроков в футбольной команде на поле?" → "11"
- "В каком году впервые прошли Олимпийские игры?" → "1896"
- "Как называется место для игры в теннис?" → "Корт"
"""
    
    # 4.2 Построение итогового промпта
    return (
        START_PROMPT +
        f"\nТема: {theme}"
        f"\nСгенерируй {questions_per_round} уникальных, точных и однозначных "
        f"вопросов для раунда {round_num}. "
        f"Все вопросы должны быть строго уровня сложности: {difficulty}. "
        "КРИТИЧЕСКИ ВАЖНО: каждый вопрос должен иметь ЕДИНСТВЕННЫЙ правильный ответ, "
        "который нельзя трактовать по-разному. "
        "Избегай вопросов, где может быть несколько правильных вариантов ответа. "
        "Формулируй вопросы максимально конкретно и недвусмысленно. "
        + sport_examples +
        "\n\nФормат ответа: JSON-массив объектов с полями: "
        "question, answer, difficulty (easy/medium/hard). "
        "Верни только JSON-массив, без обёртки и лишнего текста. "
        f"{history_text}"
    )
```

**Компоненты промпта:**
- 🎯 **Системная роль**: "Ты AI-ведущий интеллектуального квиза"
- 📚 **Тема**: Конкретная тема для вопросов
- 🎚️ **Сложность**: easy/medium/hard
- 📊 **Количество**: Точное число вопросов
- 🚫 **История**: Список для избежания дублей
- 📋 **Формат**: Строгий JSON формат
- ⚠️ **Требования**: Однозначность ответов

### **ШАГ 5: Запрос к OpenAI API**

```python
# 5.1 Получение API ключа
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_KEY:
    try:
        with open('openai_key.txt', 'r', encoding='utf-8') as f:
            OPENAI_KEY = f.read().strip()
    except FileNotFoundError:
        # Ошибка: ключ не найден
        return [{"question": "❌ OpenAI API ключ не настроен", 
                "answer": "N/A", "difficulty": "medium"}]

# 5.2 Валидация ключа
if not OPENAI_KEY or not OPENAI_KEY.startswith('sk-'):
    return [{"question": "❌ Неверный OpenAI API ключ", 
            "answer": "N/A", "difficulty": "medium"}]

# 5.3 Подготовка запроса
headers = {
    'Authorization': f'Bearer {OPENAI_KEY}',
    'Content-Type': 'application/json',
}

data = {
    "model": "gpt-4o",                    # Модель GPT-4 Omni
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 1024,                   # Максимум токенов
    "temperature": 0.2                    # Низкая температура для точности
}

# 5.4 Отправка запроса
async with aiohttp.ClientSession() as session:
    async with session.post('https://api.openai.com/v1/chat/completions', 
                          headers=headers, json=data) as resp:
        # Проверка статуса ответа
        if resp.status != 200:
            error_text = await resp.text()
            return [{"question": f"Ошибка OpenAI API (HTTP {resp.status})", 
                    "answer": "N/A", "difficulty": "medium"}]
```

**Параметры запроса:**
- 🤖 **Модель**: gpt-4o (GPT-4 Omni)
- 🎯 **Temperature**: 0.2 (низкая для точности)
- 📊 **Max tokens**: 1024 (достаточно для 5-10 вопросов)
- 🔧 **System prompt**: Роль AI-ведущего квиза
- 📝 **User prompt**: Подробные инструкции

### **ШАГ 6: Обработка ответа OpenAI**

```python
# 6.1 Парсинг JSON ответа
try:
    result = await resp.json()
except Exception as e:
    return [{"question": "Ошибка парсинга ответа OpenAI", 
            "answer": "N/A", "difficulty": "medium"}]

# 6.2 Проверка структуры ответа
if not isinstance(result, dict):
    return [{"question": "Ошибка генерации вопросов", 
            "answer": "N/A", "difficulty": "medium"}]

# 6.3 Проверка на ошибки API
if 'error' in result:
    error_msg = result['error'].get('message', 'Unknown error')
    return [{"question": f"Ошибка OpenAI: {error_msg}", 
            "answer": "N/A", "difficulty": "medium"}]

# 6.4 Извлечение контента
if 'choices' not in result or not result['choices']:
    return [{"question": "Ошибка генерации вопросов", 
            "answer": "N/A", "difficulty": "medium"}]

# 6.5 Очистка от markdown разметки
text = result['choices'][0]['message']['content']
text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
text = text.strip()

# 6.6 Парсинг JSON с вопросами
try:
    questions = json.loads(text)
except Exception as e:
    return [{"question": "Ошибка парсинга вопросов", 
            "answer": "N/A", "difficulty": "medium"}]
```

**Пример ответа OpenAI:**
```json
[
  {
    "question": "В каком году была Полтавская битва?",
    "answer": "1709",
    "difficulty": "medium"
  },
  {
    "question": "Кто был первым императором России?",
    "answer": "Петр I",
    "difficulty": "medium"
  }
]
```

### **ШАГ 7: Проверка дублирования**

```python
# 7.1 Создание множества для быстрого поиска
unique_questions = []
history_set = set(q.strip().lower() for q in history_questions)

# 7.2 Фильтрация дублей
for q in questions:
    q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
    if q_text.strip().lower() not in history_set:
        unique_questions.append(q)

# 7.3 Дополнительная генерация при недостатке вопросов
attempts = 0
while len(unique_questions) < questions_per_round and attempts < 2:
    missing = questions_per_round - len(unique_questions)
    
    # Новый запрос для недостающих вопросов
    extra_prompt = build_openai_prompt(theme, round_num, missing, 
                                     history_text, difficulty)
    
    # Повторный запрос к OpenAI
    # ... (аналогичный код запроса)
    
    attempts += 1
```

**Логика дублирования:**
- 🔍 Сравнение по нижнему регистру
- 📊 Использование set для быстрого поиска
- 🔄 Дополнительные запросы при недостатке
- 🛡️ Ограничение попыток (максимум 2)

### **ШАГ 8: Валидация и создание объектов**

**Файл:** `src/game/logic.py` → `start_round()`

```python
# 8.1 Проверка на ошибки генерации
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

# 8.2 Создание объектов Question
question_objects = []
for i, q_data in enumerate(questions_data):
    try:
        # Валидация структуры
        if not isinstance(q_data, dict):
            continue
        
        required_fields = ['question']
        if not all(field in q_data for field in required_fields):
            continue
        
        # Создание объекта Question
        question = Question.from_dict(q_data)
        question_objects.append(question)
        
    except Exception as e:
        log_error(e, f"parsing question {i}: {q_data}", chat_id)
        continue
```

**Валидация Question.from_dict():**
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Question':
    # Проверка типа данных
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}: {data}")
    
    # Проверка обязательного поля
    if 'question' not in data:
        raise ValueError(f"Question data missing 'question' field: {data}")
    
    question = data['question']
    if not question or not isinstance(question, str):
        raise ValueError(f"Question field must be non-empty string: {question}")
    
    # Получение ответа из разных полей
    correct_answer = data.get('answer', data.get('correct_answer', ''))
    if not correct_answer:
        correct_answer = 'Не указан'
    
    # Парсинг сложности
    difficulty_str = data.get('difficulty', 'medium')
    try:
        difficulty = Difficulty(difficulty_str)
    except ValueError:
        difficulty = Difficulty.MEDIUM
    
    return cls(
        question=question,
        correct_answer=correct_answer,
        difficulty=difficulty,
        explanation=data.get('explanation', '')
    )
```

### **ШАГ 9: Сохранение в игровое состояние**

```python
# 9.1 Проверка успешности создания
if not question_objects:
    await context.bot.send_message(
        chat_id, 
        "❌ Не удалось создать вопросы из ответа OpenAI.\n"
        "Попробуйте изменить тему или проверьте настройки API."
    )
    return

# 9.2 Сохранение в игровое состояние
game_state.questions = question_objects
game_state.question_index = 0

# 9.3 Запуск показа вопросов
await ask_next_question(context, chat_id)
```

### **ШАГ 10: Сохранение в историю**

```python
# 10.1 Добавление в базу данных
for q in unique_questions:
    q_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
    add_question_to_history(theme, q_text)
```

**Функция add_question_to_history():**
```python
def add_question_to_history(theme: str, question: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO questions_history (theme, question) VALUES (?, ?)', 
                    (theme, question))
        conn.commit()
```

## 🚨 Обработка ошибок и фолбэки

### **Типы ошибок:**

1. **Отсутствие API ключа**
   ```python
   return [{"question": "❌ OpenAI API ключ не настроен", 
           "answer": "N/A", "difficulty": "medium"}]
   ```

2. **HTTP ошибки**
   ```python
   if resp.status != 200:
       error_text = await resp.text()
       return [{"question": f"Ошибка OpenAI API (HTTP {resp.status})", 
               "answer": "N/A", "difficulty": "medium"}]
   ```

3. **Ошибки парсинга JSON**
   ```python
   except Exception as e:
       return [{"question": "Ошибка парсинга ответа OpenAI", 
               "answer": "N/A", "difficulty": "medium"}]
   ```

4. **Ошибки OpenAI API**
   ```python
   if 'error' in result:
       error_msg = result['error'].get('message', 'Unknown error')
       return [{"question": f"Ошибка OpenAI: {error_msg}", 
               "answer": "N/A", "difficulty": "medium"}]
   ```

### **Фолбэки:**

1. **Дополнительные запросы** при недостатке вопросов
2. **Значения по умолчанию** для отсутствующих полей
3. **Graceful degradation** - показ ошибки вместо краха

## 📊 Примеры данных на каждом этапе

### **Входные данные:**
```python
theme = "История России"
difficulty = "medium"
questions_per_round = 3
round_num = 1
```

### **Промпт для OpenAI:**
```
Ты AI-ведущий интеллектуального квиза.
Тема: История России
Сгенерируй 3 уникальных, точных и однозначных вопросов для раунда 1.
Все вопросы должны быть строго уровня сложности: medium.
КРИТИЧЕСКИ ВАЖНО: каждый вопрос должен иметь ЕДИНСТВЕННЫЙ правильный ответ...
```

### **Ответ OpenAI:**
```json
[
  {
    "question": "В каком году была Полтавская битва?",
    "answer": "1709",
    "difficulty": "medium"
  },
  {
    "question": "Кто основал Санкт-Петербург?",
    "answer": "Петр I",
    "difficulty": "medium"
  }
]
```

### **Итоговые объекты Question:**
```python
[
  Question(
    question="В каком году была Полтавская битва?",
    correct_answer="1709",
    difficulty=Difficulty.MEDIUM,
    explanation=""
  ),
  Question(
    question="Кто основал Санкт-Петербург?",
    correct_answer="Петр I",
    difficulty=Difficulty.MEDIUM,
    explanation=""
  )
]
```

## 🎯 Итоговая логика процесса

```python
def generate_questions_logic(theme, difficulty, count, round_num):
    """Псевдокод полного процесса"""
    
    # ШАГ 1: Валидация входных данных
    if not validate_input(theme, difficulty, count):
        return error_response()
    
    # ШАГ 2: Получение истории
    history = get_history(theme, limit=50)
    
    # ШАГ 3: Построение промпта
    prompt = build_prompt(theme, difficulty, count, round_num, history)
    
    # ШАГ 4: Запрос к OpenAI
    response = await openai_request(prompt)
    
    # ШАГ 5: Обработка ответа
    questions_data = parse_response(response)
    
    # ШАГ 6: Фильтрация дублей
    unique_questions = filter_duplicates(questions_data, history)
    
    # ШАГ 7: Дополнительная генерация при необходимости
    if len(unique_questions) < count:
        additional = generate_additional(theme, difficulty, 
                                       count - len(unique_questions))
        unique_questions.extend(additional)
    
    # ШАГ 8: Создание объектов Question
    question_objects = create_question_objects(unique_questions)
    
    # ШАГ 9: Сохранение в историю
    save_to_history(theme, unique_questions)
    
    # ШАГ 10: Возврат результата
    return question_objects
```

---

**Дата анализа:** 2025-07-10  
**Версия:** Quiz Bot 2.0 Detailed Steps  
**Статус:** ✅ Полная документация процесса