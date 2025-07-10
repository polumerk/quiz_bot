"""
Типы вопросов для Quiz Bot 2.0
"""

from enum import Enum
from typing import Dict, List


class QuestionType(Enum):
    """Типы вопросов"""
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
        "examples": [
            "Столица Франции?",
            "Автор романа 'Война и мир'?",
            "Химический символ золота?"
        ],
        "template": "Что/Кто/Где/Когда/Какой..."
    },
    
    QuestionType.LOGICAL: {
        "description": "Логические вопросы и задачи",
        "instruction": "Создай вопрос, требующий логического размышления",
        "examples": [
            "Если все розы - цветы, а некоторые цветы красные, то...",
            "Что тяжелее: килограмм ваты или килограмм железа?",
            "В комнате 4 угла, в каждом углу сидит кошка. Напротив каждой кошки..."
        ],
        "template": "Если... то..."
    },
    
    QuestionType.ASSOCIATIVE: {
        "description": "Вопросы на ассоциации (стиль ЧГК)",
        "instruction": "Создай вопрос с описанием, требующий найти связь или догадаться по намекам",
        "examples": [
            "Этот металл назван в честь планеты, которая в свою очередь названа в честь римского бога войны. Назовите металл.",
            "В черном ящике находится то, что в Древнем Риме называли 'слезами богов'. Что в черном ящике?",
            "Его имя означает 'подобный богу', а его самое известное изобретение помогло человечеству сохранить знания. Кто он?"
        ],
        "template": "Описание... Что это/Кто это?"
    },
    
    QuestionType.CHRONOLOGICAL: {
        "description": "Вопросы на хронологию событий",
        "instruction": "Создай вопрос о временной последовательности или датах",
        "examples": [
            "Что произошло раньше: падение Берлинской стены или распад СССР?",
            "В каком году был основан Санкт-Петербург?",
            "Расположите в хронологическом порядке: изобретение книгопечатания, открытие Америки, начало Реформации"
        ],
        "template": "Когда/Что раньше/В каком году..."
    },
    
    QuestionType.GEOGRAPHICAL: {
        "description": "Географические вопросы",
        "instruction": "Вопрос о местоположении, расстояниях, географических объектах",
        "examples": [
            "Какая река разделяет Москву на две части?",
            "Назовите самое глубокое озеро в мире",
            "В какой стране находится гора Килиманджаро?"
        ],
        "template": "Где/В какой стране/Какая река..."
    },
    
    QuestionType.MATHEMATICAL: {
        "description": "Математические вопросы",
        "instruction": "Вопрос с числами, расчетами или математическими понятиями",
        "examples": [
            "Сколько градусов в прямом угле?",
            "Чему равна сумма углов треугольника?",
            "Какое число является результатом деления любого числа на само себя?"
        ],
        "template": "Сколько/Чему равно/Вычислите..."
    },
    
    QuestionType.CULTURAL: {
        "description": "Вопросы по культуре и искусству",
        "instruction": "Вопрос о литературе, музыке, живописи, кино, театре",
        "examples": [
            "Кто написал 'Лунную сонату'?",
            "В каком музее находится 'Мона Лиза'?",
            "Как называется знаменитый роман Михаила Булгакова о дьяволе в Москве?"
        ],
        "template": "Кто автор/В каком музее/Как называется..."
    }
}


def get_question_type_prompt(question_type: QuestionType, theme: str) -> str:
    """Получить промпт для конкретного типа вопроса"""
    type_info = QUESTION_TYPE_DESCRIPTIONS[question_type]
    
    return f"""
ТИП ВОПРОСА: {type_info['description']}
ИНСТРУКЦИЯ: {type_info['instruction']}
ТЕМА: {theme}
ШАБЛОН: {type_info['template']}

ПРИМЕРЫ ФОРМАТА:
{chr(10).join(f"- {example}" for example in type_info['examples'])}
"""


def determine_question_type(theme: str, difficulty: str) -> QuestionType:
    """Определить наиболее подходящий тип вопроса для темы"""
    theme_lower = theme.lower()
    
    # Маппинг тем на типы вопросов
    if any(word in theme_lower for word in ['история', 'исторический', 'древний', 'война']):
        return QuestionType.CHRONOLOGICAL
    
    elif any(word in theme_lower for word in ['география', 'страна', 'город', 'река', 'гора']):
        return QuestionType.GEOGRAPHICAL
    
    elif any(word in theme_lower for word in ['математика', 'физика', 'число', 'формула']):
        return QuestionType.MATHEMATICAL
    
    elif any(word in theme_lower for word in ['литература', 'музыка', 'искусство', 'кино', 'театр']):
        return QuestionType.CULTURAL
    
    elif any(word in theme_lower for word in ['логика', 'головоломка', 'задача']):
        return QuestionType.LOGICAL
    
    # Для сложного уровня предпочитаем ассоциативные вопросы
    elif difficulty == 'hard':
        return QuestionType.ASSOCIATIVE
    
    # По умолчанию - фактические вопросы
    else:
        return QuestionType.FACTUAL


def mix_question_types(count: int, primary_type: QuestionType) -> List[QuestionType]:
    """
    Создать микс типов вопросов для разнообразия
    70% - основной тип, 30% - другие типы
    """
    if count <= 3:
        # Для малого количества используем только основной тип
        return [primary_type] * count
    
    primary_count = int(count * 0.7)
    other_count = count - primary_count
    
    # Выбираем другие типы
    all_types = list(QuestionType)
    all_types.remove(primary_type)
    
    result = [primary_type] * primary_count
    
    # Добавляем разнообразие
    for i in range(other_count):
        if all_types:
            other_type = all_types[i % len(all_types)]
            result.append(other_type)
    
    # Перемешиваем для разнообразия
    import random
    random.shuffle(result)
    
    return result