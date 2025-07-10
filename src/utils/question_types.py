"""
Система типов вопросов для Quiz Bot 2.0
"""

from enum import Enum
from typing import Dict, List, Optional
import random

class QuestionType(Enum):
    """Типы вопросов для интеллектуальных игр"""
    FACTUAL = "factual"
    LOGICAL = "logical"
    ASSOCIATIVE = "associative"
    CHRONOLOGICAL = "chronological"
    GEOGRAPHICAL = "geographical"
    MATHEMATICAL = "mathematical"
    CULTURAL = "cultural"
    SCIENTIFIC = "scientific"
    HISTORICAL = "historical"
    SPORTS = "sports"

QUESTION_TYPE_DESCRIPTIONS = {
    QuestionType.FACTUAL: {
        "description": "Фактические вопросы на знание",
        "instruction": "Задай прямой вопрос на знание конкретного факта",
        "examples": [
            "Столица Франции?",
            "Автор романа 'Война и мир'?",
            "Сколько планет в Солнечной системе?"
        ],
        "prompt_addition": "Используй конкретные факты, даты, имена, цифры"
    },
    QuestionType.LOGICAL: {
        "description": "Логические вопросы и задачи",
        "instruction": "Создай вопрос, требующий логического размышления",
        "examples": [
            "Если все A - B, а все B - C, то что можно сказать об A и C?",
            "В корзине 5 яблок и 3 груши. Сколько всего фруктов?",
            "Какое число должно быть следующим: 2, 4, 8, 16?"
        ],
        "prompt_addition": "Требуй логического анализа, последовательности, причинно-следственных связей"
    },
    QuestionType.ASSOCIATIVE: {
        "description": "Вопросы на ассоциации (стиль ЧГК)",
        "instruction": "Создай вопрос с описанием, требующий найти связь",
        "examples": [
            "Этот металл назван в честь планеты, которая в свою очередь названа в честь римского бога войны",
            "Этот город называют 'городом мостов', хотя мостов в нем меньше, чем в Венеции",
            "Этот писатель создал персонажа, чье имя стало нарицательным для обозначения скупости"
        ],
        "prompt_addition": "Используй описания, ассоциации, косвенные указания"
    },
    QuestionType.CHRONOLOGICAL: {
        "description": "Вопросы на хронологию событий",
        "instruction": "Создай вопрос о временной последовательности",
        "examples": [
            "Что произошло раньше: падение Берлинской стены или распад СССР?",
            "В каком порядке были основаны города: Москва, Санкт-Петербург, Екатеринбург?",
            "Какое событие произошло между открытием Америки и первой высадкой на Луну?"
        ],
        "prompt_addition": "Фокусируйся на датах, последовательности, временных рамках"
    },
    QuestionType.GEOGRAPHICAL: {
        "description": "Географические вопросы",
        "instruction": "Создай вопрос о географических объектах и явлениях",
        "examples": [
            "Какая река протекает через Париж?",
            "В какой стране находится гора Килиманджаро?",
            "Какой океан самый глубокий?"
        ],
        "prompt_addition": "Используй названия стран, городов, рек, гор, координаты, статистику"
    },
    QuestionType.MATHEMATICAL: {
        "description": "Математические вопросы",
        "instruction": "Создай вопрос с математическими вычислениями",
        "examples": [
            "Сколько будет 15% от 200?",
            "Площадь круга с радиусом 5 см равна...",
            "Сколько секунд в одном дне?"
        ],
        "prompt_addition": "Требуй вычислений, формул, математических операций"
    },
    QuestionType.CULTURAL: {
        "description": "Культурные и искусствоведческие вопросы",
        "instruction": "Создай вопрос о культуре, искусстве, литературе",
        "examples": [
            "Кто написал картину 'Мона Лиза'?",
            "В каком стиле построен собор Василия Блаженного?",
            "Какой композитор написал 'Лунную сонату'?"
        ],
        "prompt_addition": "Фокусируйся на искусстве, литературе, архитектуре, музыке"
    },
    QuestionType.SCIENTIFIC: {
        "description": "Научные вопросы",
        "instruction": "Создай вопрос о науке, открытиях, изобретениях",
        "examples": [
            "Какой элемент обозначается символом Fe?",
            "Кто открыл периодический закон?",
            "В каком году была открыта структура ДНК?"
        ],
        "prompt_addition": "Используй научные термины, имена ученых, формулы, открытия"
    },
    QuestionType.HISTORICAL: {
        "description": "Исторические вопросы",
        "instruction": "Создай вопрос об исторических событиях и личностях",
        "examples": [
            "В каком году была Куликовская битва?",
            "Кто был первым императором России?",
            "Какое событие положило конец Второй мировой войне?"
        ],
        "prompt_addition": "Фокусируйся на датах, исторических личностях, событиях, причинах"
    },
    QuestionType.SPORTS: {
        "description": "Спортивные вопросы",
        "instruction": "Создай вопрос о спорте, рекордах, правилах",
        "examples": [
            "Сколько игроков в футбольной команде на поле?",
            "В каком году прошли первые Олимпийские игры современности?",
            "Кто забил победный гол в финале ЧМ-2018?"
        ],
        "prompt_addition": "Используй спортивные термины, рекорды, правила игр, имена спортсменов"
    }
}

def get_question_type_prompt(question_type: QuestionType, theme: str) -> str:
    """Получить промпт для конкретного типа вопроса"""
    type_info = QUESTION_TYPE_DESCRIPTIONS[question_type]
    
    return f"""
    ТИП ВОПРОСА: {type_info['description']}
    ИНСТРУКЦИЯ: {type_info['instruction']}
    ТЕМА: {theme}
    
    СПЕЦИАЛЬНЫЕ ТРЕБОВАНИЯ:
    {type_info['prompt_addition']}
    
    ПРИМЕРЫ ФОРМАТА:
    {chr(10).join(f"- {example}" for example in type_info['examples'])}
    """

def determine_question_type(theme: str) -> QuestionType:
    """Определить тип вопроса на основе темы"""
    theme_lower = theme.lower()
    
    type_mapping = {
        'история': QuestionType.HISTORICAL,
        'география': QuestionType.GEOGRAPHICAL,
        'наука': QuestionType.SCIENTIFIC,
        'спорт': QuestionType.SPORTS,
        'культура': QuestionType.CULTURAL,
        'математика': QuestionType.MATHEMATICAL,
        'логика': QuestionType.LOGICAL,
        'ассоциации': QuestionType.ASSOCIATIVE,
        'хронология': QuestionType.CHRONOLOGICAL
    }
    
    # Проверяем точные совпадения
    for key, question_type in type_mapping.items():
        if key in theme_lower:
            return question_type
    
    # Проверяем частичные совпадения
    if any(word in theme_lower for word in ['истори', 'война', 'царь', 'император']):
        return QuestionType.HISTORICAL
    elif any(word in theme_lower for word in ['географ', 'страна', 'город', 'река', 'гора']):
        return QuestionType.GEOGRAPHICAL
    elif any(word in theme_lower for word in ['наука', 'физика', 'химия', 'биология']):
        return QuestionType.SCIENTIFIC
    elif any(word in theme_lower for word in ['спорт', 'футбол', 'олимпиада', 'игра']):
        return QuestionType.SPORTS
    elif any(word in theme_lower for word in ['культура', 'искусство', 'литература', 'музыка']):
        return QuestionType.CULTURAL
    elif any(word in theme_lower for word in ['математика', 'число', 'вычисление']):
        return QuestionType.MATHEMATICAL
    elif any(word in theme_lower for word in ['логика', 'последовательность']):
        return QuestionType.LOGICAL
    elif any(word in theme_lower for word in ['ассоциация', 'связь']):
        return QuestionType.ASSOCIATIVE
    elif any(word in theme_lower for word in ['хронология', 'время', 'дата']):
        return QuestionType.CHRONOLOGICAL
    
    # По умолчанию возвращаем фактический тип
    return QuestionType.FACTUAL

def get_all_question_types() -> List[QuestionType]:
    """Получить все доступные типы вопросов"""
    return list(QuestionType)

def get_question_type_description(question_type: QuestionType) -> str:
    """Получить описание типа вопроса"""
    return QUESTION_TYPE_DESCRIPTIONS[question_type]["description"]

def get_random_question_type(theme: str = "") -> QuestionType:
    """Случайно выбрать тип вопроса (с приоритетом по теме, если возможно)"""
    # Сначала пробуем тематический тип
    thematic_type = determine_question_type(theme)
    all_types = get_all_question_types()
    # 50% шанс выбрать тематический, 50% — любой другой
    if random.random() < 0.5:
        return thematic_type
    else:
        return random.choice(all_types)