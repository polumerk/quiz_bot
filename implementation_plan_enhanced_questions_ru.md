# План реализации улучшений системы генерации вопросов Quiz Bot 2.0

## Этап 1: Критические улучшения (2-3 недели)

### 1.1 Расширенный формат вопросов с пояснениями

**Задача**: Добавить пояснения к ответам для образовательной ценности

**Изменения в models.py**:
```python
class Question(BaseModel):
    question: str
    answer: str
    explanation: str = ""  # Новое поле
    interesting_fact: str = ""  # Новое поле
    source_type: str = "general"  # Новое поле
    difficulty_level: int = 5  # Новое поле (1-10)
    
    # Дополнительные поля для будущего расширения
    tags: List[str] = []
    alternative_answers: List[str] = []
    estimated_time: str = "30 секунд"
```

**Изменения в utils/openai_helper.py**:
```python
def build_enhanced_prompt(settings):
    base_prompt = build_openai_prompt(settings)
    
    enhanced_prompt = f"""
    {base_prompt}
    
    ВАЖНО: Каждый вопрос должен нести образовательную ценность!
    
    ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
    1. Добавь краткое пояснение к правильному ответу (1-2 предложения)
    2. Включи интересный факт, связанный с темой (1 предложение)
    3. Укажи тип источника: энциклопедия, учебник, документ, новости
    4. Оцени сложность от 1 до 10 (где 1 - детский сад, 10 - экспертный уровень)
    
    ФОРМАТ JSON:
    {{
      "questions": [
        {{
          "question": "Текст вопроса",
          "answer": "Правильный ответ",
          "explanation": "Пояснение почему этот ответ правильный",
          "interesting_fact": "Интересный факт по теме",
          "source_type": "энциклопедия",
          "difficulty_level": 7
        }}
      ]
    }}
    """
    
    return enhanced_prompt
```

### 1.2 Система типов вопросов

**Новый файл**: `utils/question_types.py`
```python
from enum import Enum
from typing import Dict, List

class QuestionType(Enum):
    FACTUAL = "factual"
    LOGICAL = "logical"
    ASSOCIATIVE = "associative"
    CHRONOLOGICAL = "chronological"
    GEOGRAPHICAL = "geographical"
    MATHEMATICAL = "mathematical"
    CULTURAL = "cultural"

QUESTION_TYPE_DESCRIPTIONS = {
    QuestionType.FACTUAL: {
        "description": "Фактические вопросы на знание",
        "instruction": "Задай прямой вопрос на знание конкретного факта",
        "examples": ["Столица Франции?", "Автор романа 'Война и мир'?"]
    },
    QuestionType.LOGICAL: {
        "description": "Логические вопросы и задачи",
        "instruction": "Создай вопрос, требующий логического размышления",
        "examples": ["Если все A - B, а все B - C, то...?"]
    },
    QuestionType.ASSOCIATIVE: {
        "description": "Вопросы на ассоциации (стиль ЧГК)",
        "instruction": "Создай вопрос с описанием, требующий найти связь",
        "examples": ["Этот металл назван в честь планеты, которая в свою очередь названа в честь римского бога войны"]
    },
    QuestionType.CHRONOLOGICAL: {
        "description": "Вопросы на хронологию событий",
        "instruction": "Создай вопрос о временной последовательности",
        "examples": ["Что произошло раньше: падение Берлинской стены или распад СССР?"]
    }
}

def get_question_type_prompt(question_type: QuestionType, theme: str) -> str:
    """Получить промпт для конкретного типа вопроса"""
    type_info = QUESTION_TYPE_DESCRIPTIONS[question_type]
    
    return f"""
    ТИП ВОПРОСА: {type_info['description']}
    ИНСТРУКЦИЯ: {type_info['instruction']}
    ТЕМА: {theme}
    
    ПРИМЕРЫ ФОРМАТА:
    {chr(10).join(f"- {example}" for example in type_info['examples'])}
    """
```

### 1.3 Система проверки качества

**Новый файл**: `utils/quality_checker.py`
```python
import re
from typing import Dict, List, Tuple

class QualityChecker:
    def __init__(self):
        self.ambiguous_words = [
            "может быть", "возможно", "иногда", "часто", "обычно", 
            "некоторые", "многие", "несколько"
        ]
        
        self.required_specificity = {
            'dates': r'\d{4}',  # Требуем конкретные годы
            'numbers': r'\d+',   # Требуем конкретные цифры
            'names': r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+',  # Имя и фамилия
        }
    
    def check_question_quality(self, question_data: Dict) -> Tuple[int, List[str]]:
        """
        Проверить качество вопроса
        Возвращает: (оценка 1-10, список проблем)
        """
        score = 10
        issues = []
        
        question = question_data.get('question', '')
        answer = question_data.get('answer', '')
        
        # Проверка на неоднозначность
        if self._is_ambiguous(question):
            score -= 3
            issues.append("Вопрос содержит неоднозначные формулировки")
        
        # Проверка на конкретность ответа
        if self._is_vague_answer(answer):
            score -= 2
            issues.append("Ответ недостаточно конкретен")
        
        # Проверка на грамматику
        if self._has_grammar_issues(question):
            score -= 1
            issues.append("Возможные грамматические ошибки")
        
        # Проверка на актуальность
        if self._needs_date_verification(question):
            score -= 1
            issues.append("Требуется проверка актуальности данных")
        
        return max(1, score), issues
    
    def _is_ambiguous(self, question: str) -> bool:
        """Проверить на неоднозначность"""
        return any(word in question.lower() for word in self.ambiguous_words)
    
    def _is_vague_answer(self, answer: str) -> bool:
        """Проверить на конкретность ответа"""
        return len(answer.split()) < 2 and not re.search(r'\d+', answer)
    
    def _has_grammar_issues(self, question: str) -> bool:
        """Простая проверка на грамматические ошибки"""
        # Проверка на повторяющиеся слова
        words = question.lower().split()
        return len(words) != len(set(words))
    
    def _needs_date_verification(self, question: str) -> bool:
        """Проверить, нужна ли проверка актуальности"""
        date_indicators = ['сейчас', 'в настоящее время', 'сегодня', 'текущий']
        return any(indicator in question.lower() for indicator in date_indicators)
```

## Этап 2: Важные улучшения (3-4 недели)

### 2.1 Интеграция системы качества в основной процесс

**Изменения в handlers/question_generation.py**:
```python
from utils.quality_checker import QualityChecker
from utils.question_types import QuestionType, get_question_type_prompt

class QuestionGenerator:
    def __init__(self):
        self.quality_checker = QualityChecker()
    
    async def generate_questions_with_quality_check(self, settings: dict) -> List[Dict]:
        """Генерация вопросов с проверкой качества"""
        
        # Определяем тип вопросов на основе темы
        question_type = self._determine_question_type(settings.get('theme', 'general'))
        
        # Генерируем вопросы
        raw_questions = await self._generate_raw_questions(settings, question_type)
        
        # Проверяем качество и фильтруем
        quality_questions = []
        for question_data in raw_questions:
            score, issues = self.quality_checker.check_question_quality(question_data)
            
            if score >= 7:  # Принимаем только качественные вопросы
                quality_questions.append(question_data)
            else:
                logger.warning(f"Вопрос отклонен (оценка {score}): {issues}")
        
        return quality_questions
    
    def _determine_question_type(self, theme: str) -> QuestionType:
        """Определить тип вопроса на основе темы"""
        type_mapping = {
            'history': QuestionType.CHRONOLOGICAL,
            'geography': QuestionType.GEOGRAPHICAL,
            'science': QuestionType.FACTUAL,
            'sports': QuestionType.FACTUAL,
            'general': QuestionType.FACTUAL
        }
        return type_mapping.get(theme, QuestionType.FACTUAL)
```

### 2.2 Система статистики и аналитики

**Новый файл**: `utils/analytics.py`
```python
from typing import Dict, List
from datetime import datetime
import json

class QuestionAnalytics:
    def __init__(self):
        self.stats = {
            'total_generated': 0,
            'quality_distribution': {},
            'theme_performance': {},
            'difficulty_accuracy': {},
            'question_types': {}
        }
    
    def track_question_generation(self, questions: List[Dict], settings: Dict):
        """Отслеживать статистику генерации вопросов"""
        self.stats['total_generated'] += len(questions)
        
        # Отслеживаем качество
        for question in questions:
            difficulty = question.get('difficulty_level', 5)
            theme = settings.get('theme', 'general')
            
            self._update_quality_stats(difficulty)
            self._update_theme_stats(theme, len(questions))
    
    def track_game_results(self, game_results: Dict):
        """Отслеживать результаты игры для улучшения генерации"""
        for question_result in game_results.get('questions', []):
            difficulty = question_result.get('difficulty_level', 5)
            was_correct = question_result.get('correct', False)
            
            self._update_difficulty_accuracy(difficulty, was_correct)
    
    def get_recommendations(self) -> Dict:
        """Получить рекомендации по улучшению генерации"""
        recommendations = {}
        
        # Анализ точности по сложности
        for difficulty, stats in self.stats['difficulty_accuracy'].items():
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            if accuracy < 0.3:
                recommendations[f'difficulty_{difficulty}'] = "Слишком сложные вопросы"
            elif accuracy > 0.9:
                recommendations[f'difficulty_{difficulty}'] = "Слишком простые вопросы"
        
        return recommendations
```

### 2.3 Улучшенная система промптов

**Обновление utils/openai_helper.py**:
```python
def build_professional_prompt(settings: dict) -> str:
    """Создать профессиональный промпт по образцу лучших практик"""
    
    theme = settings.get('theme', 'general')
    difficulty = settings.get('difficulty', 'medium')
    questions_count = settings.get('questions_count', 10)
    question_type = settings.get('question_type', 'factual')
    
    # Базовые инструкции по качеству
    quality_instructions = """
    СТАНДАРТЫ КАЧЕСТВА (по образцу "Что? Где? Когда?"):
    1. Вопрос должен иметь ЕДИНСТВЕННЫЙ правильный ответ
    2. Формулировка должна быть ТОЧНОЙ и НЕДВУСМЫСЛЕННОЙ
    3. Ответ должен быть КОНКРЕТНЫМ (избегай "примерно", "около", "может быть")
    4. Добавь ОБРАЗОВАТЕЛЬНУЮ ЦЕННОСТЬ через пояснения
    5. Включи ИНТЕРЕСНЫЙ ФАКТ для запоминания
    """
    
    # Инструкции по сложности
    difficulty_instructions = {
        'easy': "Уровень: школьные знания, общеизвестные факты (точность 85-95%)",
        'medium': "Уровень: образованный человек, требует размышлений (точность 60-80%)",
        'hard': "Уровень: экспертные знания, специализированная информация (точность 30-50%)"
    }
    
    # Тематические инструкции
    theme_instructions = {
        'sports': "Конкретные цифры, даты, имена спортсменов, правила игр",
        'history': "Точные даты, исторические личности, причинно-следственные связи",
        'science': "Научные факты, открытия, формулы, имена ученых",
        'geography': "Точные названия, координаты, статистические данные"
    }
    
    return f"""
    Ты профессиональный составитель вопросов для интеллектуальных игр.
    
    {quality_instructions}
    
    НАСТРОЙКИ ИГРЫ:
    - Тема: {theme}
    - Сложность: {difficulty_instructions.get(difficulty, '')}
    - Количество вопросов: {questions_count}
    - Тип вопросов: {question_type}
    
    ТЕМАТИЧЕСКИЕ ТРЕБОВАНИЯ:
    {theme_instructions.get(theme, 'Общие знания, разнообразные темы')}
    
    ФОРМАТ ОТВЕТА (строго JSON):
    {{
      "questions": [
        {{
          "question": "Четко сформулированный вопрос",
          "answer": "Конкретный ответ",
          "explanation": "Пояснение ответа в 1-2 предложениях",
          "interesting_fact": "Интересный факт по теме",
          "source_type": "энциклопедия/учебник/документ",
          "difficulty_level": 7,
          "tags": ["тег1", "тег2"]
        }}
      ]
    }}
    
    Создай {questions_count} вопросов высокого качества!
    """
```

## Этап 3: Долгосрочные цели (1-2 месяца)

### 3.1 Система обратной связи

**Новый файл**: `utils/feedback_system.py`
```python
class FeedbackSystem:
    def __init__(self):
        self.question_ratings = {}
        self.improvement_suggestions = []
    
    def rate_question(self, question_id: str, rating: int, comment: str = ""):
        """Оценить вопрос пользователем"""
        if question_id not in self.question_ratings:
            self.question_ratings[question_id] = []
        
        self.question_ratings[question_id].append({
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now()
        })
    
    def get_question_average_rating(self, question_id: str) -> float:
        """Получить среднюю оценку вопроса"""
        ratings = self.question_ratings.get(question_id, [])
        if not ratings:
            return 0.0
        
        return sum(r['rating'] for r in ratings) / len(ratings)
    
    def suggest_improvements(self) -> List[str]:
        """Получить предложения по улучшению на основе feedback"""
        low_rated_questions = []
        
        for question_id, ratings in self.question_ratings.items():
            avg_rating = self.get_question_average_rating(question_id)
            if avg_rating < 3.0:
                low_rated_questions.append(question_id)
        
        return [
            f"Вопрос {qid} получил низкую оценку - пересмотреть"
            for qid in low_rated_questions
        ]
```

### 3.2 Интеграция с внешними источниками

**Новый файл**: `utils/external_sources.py`
```python
import requests
from typing import Dict, List

class ExternalSourcesIntegrator:
    def __init__(self):
        self.sources = {
            'wikipedia': 'https://ru.wikipedia.org/api/rest_v1/',
            'wikidata': 'https://query.wikidata.org/sparql',
            'chgk_db': 'https://db.chgk.info/question/'
        }
    
    async def verify_answer(self, question: str, answer: str) -> Dict:
        """Проверить ответ через внешние источники"""
        verification_result = {
            'verified': False,
            'confidence': 0.0,
            'sources': []
        }
        
        # Проверка через Wikipedia
        wiki_result = await self._check_wikipedia(question, answer)
        if wiki_result['found']:
            verification_result['verified'] = True
            verification_result['confidence'] += 0.5
            verification_result['sources'].append('Wikipedia')
        
        return verification_result
    
    async def _check_wikipedia(self, question: str, answer: str) -> Dict:
        """Проверить через Wikipedia API"""
        # Реализация проверки через Wikipedia API
        # Упрощенная версия для примера
        return {'found': True, 'relevance': 0.8}
```

## План внедрения

### Неделя 1-2: Базовые улучшения
- ✅ Расширить модель Question с новыми полями
- ✅ Обновить промпты для генерации пояснений
- ✅ Создать систему типов вопросов
- ✅ Базовая проверка качества

### Неделя 3-4: Интеграция и тестирование
- ✅ Интегрировать проверку качества в основной процесс
- ✅ Создать систему аналитики
- ✅ Обновить пользовательский интерфейс
- ✅ Провести тестирование с реальными пользователями

### Неделя 5-8: Продвинутые функции
- ✅ Система обратной связи
- ✅ Интеграция с внешними источниками
- ✅ Расширенная аналитика
- ✅ Мультиязычность (если требуется)

## Критерии успеха

1. **Качество вопросов**: Средняя оценка качества > 7/10
2. **Образовательная ценность**: 100% вопросов с пояснениями
3. **Разнообразие**: Минимум 5 типов вопросов
4. **Точность**: Снижение жалоб на неоднозначность на 80%
5. **Пользовательская оценка**: Средняя оценка игроков > 4/5

Этот план сделает Quiz Bot 2.0 конкурентоспособным с лучшими мировыми платформами интеллектуальных игр!