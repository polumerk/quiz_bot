"""
Улучшенная система генерации вопросов для Quiz Bot 2.0
Интегрирует качество, типы вопросов, аналитику и обратную связь
"""

import json
import re
import aiohttp
import os
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime

# Импортируем новые системы
from .quality_checker import QualityChecker
from .question_types import QuestionType, determine_question_type, get_question_type_prompt
from .analytics import QuestionAnalytics
from .feedback_system import FeedbackSystem

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

SYSTEM_PROMPT_QUESTION = (
    "Ты — AI-ведущий интеллектуального квиза. "
    "Генерируй только однозначные вопросы с коротким, точным ответом. "
    "Не добавляй лишних пояснений, соблюдай формат строго."
)

class EnhancedQuestionGenerator:
    """Улучшенный генератор вопросов с проверкой качества"""
    
    def __init__(self):
        self.quality_checker = QualityChecker()
        self.analytics = QuestionAnalytics()
        self.feedback_system = FeedbackSystem()
        
        # Настройки OpenAI
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            try:
                with open('openai_key.txt', 'r', encoding='utf-8') as f:
                    self.openai_key = f.read().strip()
            except FileNotFoundError:
                print('[LOG] OpenAI API key not found')
    
    async def generate_questions_with_quality_check(
        self, 
        theme: str, 
        round_num: int, 
        chat_id: int, 
        get_difficulty, 
        get_questions_per_round,
        max_attempts: int = 3
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Генерация вопросов с проверкой качества
        Возвращает: (качественные вопросы, отклоненные вопросы)
        """
        if not self.openai_key or not self.openai_key.startswith('sk-'):
            return [{
                "question": "❌ Неверный OpenAI API ключ",
                "answer": "N/A",
                "explanation": "",
                "interesting_fact": "",
                "source_type": "general",
                "difficulty_level": 5,
                "tags": []
            }], []
        
        # Получаем настройки
        difficulty = get_difficulty(chat_id)
        questions_count = get_questions_per_round(chat_id)
        
        # Определяем тип вопросов
        question_type = determine_question_type(theme)
        
        # Генерируем вопросы
        raw_questions = await self._generate_raw_questions(
            theme, round_num, questions_count, difficulty, question_type
        )
        
        # Проверяем качество и фильтруем
        quality_questions = []
        rejected_questions = []
        
        for question_data in raw_questions:
            score, issues = self.quality_checker.check_question_quality(question_data)
            
            # Добавляем оценку качества к данным вопроса
            question_data['quality_score'] = score
            question_data['quality_issues'] = issues
            question_data['question_type'] = question_type.value
            
            if score >= 7:  # Принимаем только качественные вопросы
                quality_questions.append(question_data)
            else:
                rejected_questions.append(question_data)
                # Отслеживаем отклоненные вопросы
                self.analytics.track_rejected_question(
                    question_data, 
                    "; ".join(issues)
                )
        
        # Если качественных вопросов недостаточно, пробуем еще раз
        attempts = 0
        while len(quality_questions) < questions_count and attempts < max_attempts:
            attempts += 1
            print(f"[LOG] Попытка {attempts}: сгенерировано {len(quality_questions)} качественных вопросов из {questions_count}")
            
            additional_questions = await self._generate_raw_questions(
                theme, round_num, questions_count - len(quality_questions), difficulty, question_type
            )
            
            for question_data in additional_questions:
                score, issues = self.quality_checker.check_question_quality(question_data)
                question_data['quality_score'] = score
                question_data['quality_issues'] = issues
                question_data['question_type'] = question_type.value
                
                if score >= 7:
                    quality_questions.append(question_data)
                else:
                    rejected_questions.append(question_data)
                    self.analytics.track_rejected_question(
                        question_data, 
                        "; ".join(issues)
                    )
        
        # Отслеживаем статистику
        settings = {
            'theme': theme,
            'difficulty': difficulty,
            'questions_count': questions_count
        }
        self.analytics.track_question_generation(quality_questions, settings)
        
        return quality_questions, rejected_questions
    
    async def _generate_raw_questions(
        self, 
        theme: str, 
        round_num: int, 
        questions_count: int, 
        difficulty: str,
        question_type: QuestionType
    ) -> List[Dict]:
        """Генерация сырых вопросов через OpenAI"""
        
        # Строим профессиональный промпт
        prompt = self._build_enhanced_prompt(theme, round_num, questions_count, difficulty, question_type)
        
        headers = {
            'Authorization': f'Bearer {self.openai_key}',
            'Content-Type': 'application/json',
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.2
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.openai.com/v1/chat/completions', 
                    headers=headers, 
                    json=data
                ) as resp:
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f'[LOG] OpenAI HTTP Error {resp.status}: {error_text}')
                        return [{
                            "question": f"Ошибка OpenAI API (HTTP {resp.status})",
                            "answer": "N/A",
                            "explanation": "",
                            "interesting_fact": "",
                            "source_type": "general",
                            "difficulty_level": 5,
                            "tags": []
                        }]
                    
                    result = await resp.json()
                    
                    if 'error' in result:
                        print('[LOG] OpenAI API Error:', result['error'])
                        return [{
                            "question": f"Ошибка OpenAI: {result['error'].get('message', 'Unknown error')}",
                            "answer": "N/A",
                            "explanation": "",
                            "interesting_fact": "",
                            "source_type": "general",
                            "difficulty_level": 5,
                            "tags": []
                        }]
                    
                    if 'choices' not in result or not result['choices']:
                        print('[LOG] OpenAI response missing choices:', result)
                        return [{
                            "question": "Ошибка генерации вопросов",
                            "answer": "N/A",
                            "explanation": "",
                            "interesting_fact": "",
                            "source_type": "general",
                            "difficulty_level": 5,
                            "tags": []
                        }]
                    
                    text = result['choices'][0]['message']['content']
                    text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
                    text = text.strip()
                    
                    try:
                        questions = json.loads(text)
                        if isinstance(questions, dict) and 'questions' in questions:
                            questions = questions['questions']
                        
                        # Убеждаемся, что все вопросы имеют необходимые поля
                        enhanced_questions = []
                        for q in questions:
                            if isinstance(q, dict):
                                enhanced_q = {
                                    "question": q.get('question', ''),
                                    "answer": q.get('answer', q.get('correct_answer', '')),
                                    "explanation": q.get('explanation', ''),
                                    "interesting_fact": q.get('interesting_fact', ''),
                                    "source_type": q.get('source_type', 'general'),
                                    "difficulty_level": q.get('difficulty_level', 5),
                                    "tags": q.get('tags', []),
                                    "difficulty": q.get('difficulty', difficulty)
                                }
                                enhanced_questions.append(enhanced_q)
                        
                        return enhanced_questions
                        
                    except Exception as e:
                        print('[LOG] Ошибка парсинга OpenAI:', e)
                        return [{
                            "question": "Ошибка парсинга вопросов",
                            "answer": "N/A",
                            "explanation": "",
                            "interesting_fact": "",
                            "source_type": "general",
                            "difficulty_level": 5,
                            "tags": []
                        }]
                        
        except Exception as e:
            print(f'[LOG] Ошибка запроса к OpenAI: {e}')
            return [{
                "question": "Ошибка соединения с OpenAI",
                "answer": "N/A",
                "explanation": "",
                "interesting_fact": "",
                "source_type": "general",
                "difficulty_level": 5,
                "tags": []
            }]
    
    def _build_enhanced_prompt(
        self, 
        theme: str, 
        round_num: int, 
        questions_count: int, 
        difficulty: str,
        question_type: QuestionType
    ) -> str:
        """Создать улучшенный промпт с профессиональными стандартами"""
        
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
        
        # Получаем специфичные инструкции для типа вопроса
        type_prompt = get_question_type_prompt(question_type, theme)
        
        # Стратегии для разного количества вопросов
        if questions_count <= 3:
            quantity_strategy = """
СТРАТЕГИЯ ДЛЯ МАЛОГО КОЛИЧЕСТВА ВОПРОСОВ (1-3):
- Выбирай САМЫЕ КАЧЕСТВЕННЫЕ и показательные вопросы по теме
- Каждый вопрос должен быть ИДЕАЛЬНЫМ примером уровня сложности
- Максимальное разнообразие аспектов темы
- Фокусируйся на самых важных и интересных деталях"""
        elif questions_count <= 7:
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
        
        return f"""
Ты профессиональный составитель вопросов для интеллектуальных игр.

{quality_instructions}

ЗАДАЧА: Сгенерируй {questions_count} вопросов для темы "{theme}" (раунд {round_num})

НАСТРОЙКИ ИГРЫ:
- Тема: {theme}
- Сложность: {difficulty_instructions.get(difficulty, '')}
- Количество вопросов: {questions_count}
- Тип вопросов: {question_type.value}

{type_prompt}

{quantity_strategy}

ТЕМАТИЧЕСКИЕ ТРЕБОВАНИЯ:
{theme_instructions.get(theme, 'Общие знания, разнообразные темы')}

ОБЩИЕ ТРЕБОВАНИЯ:
- Каждый вопрос должен иметь ЕДИНСТВЕННЫЙ правильный ответ
- Формулируй максимально конкретно и недвусмысленно
- Строго соблюдай уровень сложности {difficulty}
- Избегай субъективных оценок и мнений

ВАЖНО: КАЖДЫЙ ВОПРОС ДОЛЖЕН НЕСТИ ОБРАЗОВАТЕЛЬНУЮ ЦЕННОСТЬ!

ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
1. Добавь краткое пояснение к правильному ответу (1-2 предложения)
2. Включи интересный факт, связанный с темой (1 предложение)
3. Укажи тип источника: энциклопедия, учебник, документ, научная статья
4. Оцени сложность от 1 до 10 (где 1 - детский сад, 10 - экспертный уровень)
5. Добавь 1-3 тега для категоризации вопроса

НИКОГДА НЕ ЗАДАВАЙ СУБЪЕКТИВНЫЕ ВОПРОСЫ ТИПА:
{chr(10).join(f'- "{q}"' for q in BAD_QUESTION_EXAMPLES)}

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
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Получить отчет о качестве вопросов"""
        return self.analytics.get_quality_report()
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Получить сводку обратной связи"""
        return self.feedback_system.get_feedback_summary()
    
    def get_recommendations(self) -> Dict[str, str]:
        """Получить рекомендации по улучшению"""
        analytics_recs = self.analytics.get_recommendations()
        feedback_recs = self.feedback_system.suggest_improvements()
        
        recommendations = analytics_recs.copy()
        for i, rec in enumerate(feedback_recs):
            recommendations[f'feedback_{i}'] = rec
        
        return recommendations
    
    def rate_question(self, question_id: str, user_id: int, rating: int, comment: str = ""):
        """Оценить вопрос пользователем"""
        self.feedback_system.rate_question(question_id, user_id, rating, comment)
    
    def submit_complaint(self, question_id: str, user_id: int, complaint_type: str, description: str):
        """Отправить жалобу на вопрос"""
        self.feedback_system.submit_complaint(question_id, user_id, complaint_type, description)
    
    def track_game_results(self, game_results: Dict[str, Any]):
        """Отслеживать результаты игры"""
        self.analytics.track_game_results(game_results)