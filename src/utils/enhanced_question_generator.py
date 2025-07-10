"""
Улучшенный генератор вопросов для Quiz Bot 2.0
Интегрирует систему качества, типы вопросов и аналитику
"""

import json
import re
import aiohttp
import os
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import logging
from src.config import config

# Временные заглушки для классов
class QualityChecker:
    def check_question_quality(self, question_data):
        return 7, []  # Временная реализация

class QuestionAnalytics:
    def track_question_generation(self, questions, settings):
        pass
    def track_rejected_question(self, question, reason):
        pass
    def get_quality_report(self):
        return {"error": "Not implemented yet"}
    def get_recommendations(self):
        return {}
    def track_game_results(self, game_results):
        pass

class FeedbackSystem:
    def rate_question(self, question_id, user_id, rating, comment):
        pass
    def submit_complaint(self, question_id, user_id, complaint_type, description):
        pass
    def get_feedback_summary(self):
        return {"error": "Not implemented yet"}
    def suggest_improvements(self):
        return []

class QuestionType:
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
    
    def __init__(self, value):
        self.value = value

def determine_question_type(theme):
    return QuestionType("factual")

def get_question_type_prompt(question_type, theme):
    return f"Тип вопроса: {question_type.value}, Тема: {theme}"

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
        
        # Системные промпты
        self.system_prompt = (
            "Ты профессиональный составитель вопросов для интеллектуальных игр. "
            "Создавай качественные вопросы с образовательной ценностью."
        )
        self.debug = (os.getenv('LOG_LEVEL', '').upper() == 'DEBUG') or (os.getenv('DEBUG_MODE', '').lower() == 'true') or getattr(config, 'LOG_LEVEL', 'INFO').upper() == 'DEBUG' or getattr(config, 'DEBUG_MODE', False)
    
    async def generate_questions_with_quality_check(
        self, 
        settings: Dict[str, Any],
        max_attempts: int = 3
    ) -> Tuple[List[Dict], List[Dict]]:
        print('[DEBUG] generate_questions_with_quality_check called', settings)
        """
        Генерация вопросов с проверкой качества
        Возвращает: (качественные вопросы, отклоненные вопросы)
        """
        theme = settings.get('theme', 'general')
        difficulty = settings.get('difficulty', 'medium')
        questions_count = settings.get('questions_count', 10)
        
        # Определяем тип вопросов
        question_type = determine_question_type(theme)
        
        # Генерируем вопросы
        raw_questions = await self._generate_raw_questions(settings, question_type)
        
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
                settings, question_type, questions_count - len(quality_questions)
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
        self.analytics.track_question_generation(quality_questions, settings)
        
        return quality_questions, rejected_questions
    
    async def _generate_raw_questions(
        self, 
        settings: Dict[str, Any], 
        question_type: QuestionType,
        count: Optional[int] = None
    ) -> List[Dict]:
        print('[DEBUG] _generate_raw_questions called, key:', self.openai_key)
        """Генерация сырых вопросов через OpenAI"""
        
        if not self.openai_key or not self.openai_key.startswith('sk-'):
            return [{
                "question": "❌ Неверный OpenAI API ключ",
                "answer": "N/A",
                "explanation": "",
                "interesting_fact": "",
                "source_type": "general",
                "difficulty_level": 5,
                "tags": []
            }]
        
        theme = settings.get('theme', 'general')
        difficulty = settings.get('difficulty', 'medium')
        questions_count = count or settings.get('questions_count', 10)
        
        # Строим профессиональный промпт
        prompt = self._build_professional_prompt(settings, question_type)
        
        headers = {
            'Authorization': f'Bearer {self.openai_key}',
            'Content-Type': 'application/json',
        }
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.2
        }
        
        if self.debug:
            print(f'[DEBUG] OpenAI request data: {data}')
            print(f'[DEBUG] OpenAI request headers: {headers}')
        try:
            async with aiohttp.ClientSession() as session:
                if self.debug:
                    print('[DEBUG] Sending request to OpenAI...')
                async with session.post(
                    'https://api.openai.com/v1/chat/completions', 
                    headers=headers, 
                    json=data
                ) as resp:
                    if self.debug:
                        print(f'[DEBUG] OpenAI response status: {resp.status}')
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
                    if self.debug:
                        print(f'[DEBUG] OpenAI raw response: {result}')
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
                    if self.debug:
                        print(f'[DEBUG] OpenAI content: {text}')
                    text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
                    text = text.strip()
                    
                    try:
                        questions = json.loads(text)
                        if self.debug:
                            print(f'[DEBUG] Parsed questions: {questions}')
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
                        if self.debug:
                            print(f'[DEBUG] Content for parsing: {text}')
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
            if self.debug:
                import traceback
                traceback.print_exc()
            return [{
                "question": "Ошибка соединения с OpenAI",
                "answer": "N/A",
                "explanation": "",
                "interesting_fact": "",
                "source_type": "general",
                "difficulty_level": 5,
                "tags": []
            }]
    
    def _build_professional_prompt(self, settings: Dict[str, Any], question_type: QuestionType) -> str:
        """Создать профессиональный промпт по образцу лучших практик"""
        
        theme = settings.get('theme', 'general')
        difficulty = settings.get('difficulty', 'medium')
        questions_count = settings.get('questions_count', 10)
        
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
        
        return f"""
Ты профессиональный составитель вопросов для интеллектуальных игр.

{quality_instructions}

НАСТРОЙКИ ИГРЫ:
- Тема: {theme}
- Сложность: {difficulty_instructions.get(difficulty, '')}
- Количество вопросов: {questions_count}
- Тип вопросов: {question_type.value}

{type_prompt}

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