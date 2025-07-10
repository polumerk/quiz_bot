"""
Система проверки качества вопросов для Quiz Bot 2.0
"""

import re
from typing import Dict, List, Tuple


class QualityChecker:
    """Класс для проверки качества вопросов"""
    
    def __init__(self):
        # Слова, которые делают вопрос неоднозначным
        self.ambiguous_words = [
            "может быть", "возможно", "иногда", "часто", "обычно", 
            "некоторые", "многие", "несколько", "наверное", "скорее всего",
            "примерно", "около", "где-то", "как правило", "в основном"
        ]
        
        # Слова, требующие актуальности
        self.date_indicators = [
            'сейчас', 'в настоящее время', 'сегодня', 'текущий', 
            'современный', 'на данный момент', 'ныне', 'теперь'
        ]
        
        # Регулярки для проверки специфичности
        self.required_specificity = {
            'dates': r'\d{4}',  # Требуем конкретные годы
            'numbers': r'\d+',   # Требуем конкретные цифры
            'names': r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+',  # Имя и фамилия
        }
        
        # Субъективные слова
        self.subjective_words = [
            "любимый", "лучший", "худший", "красивый", "важный",
            "интересный", "скучный", "полезный", "вредный"
        ]
    
    def check_question_quality(self, question_data: Dict) -> Tuple[int, List[str]]:
        """
        Проверить качество вопроса
        Возвращает: (оценка 1-10, список проблем)
        """
        score = 10
        issues = []
        
        question = question_data.get('question', '')
        answer = question_data.get('answer', '')
        explanation = question_data.get('explanation', '')
        
        # 1. Проверка на неоднозначность
        if self._is_ambiguous(question):
            score -= 3
            issues.append("Вопрос содержит неоднозначные формулировки")
        
        # 2. Проверка на конкретность ответа
        if self._is_vague_answer(answer):
            score -= 2
            issues.append("Ответ недостаточно конкретен")
        
        # 3. Проверка на субъективность
        if self._is_subjective(question):
            score -= 4
            issues.append("Вопрос содержит субъективные оценки")
        
        # 4. Проверка на актуальность
        if self._needs_date_verification(question):
            score -= 1
            issues.append("Требуется проверка актуальности данных")
        
        # 5. Проверка на грамматику
        if self._has_grammar_issues(question):
            score -= 1
            issues.append("Возможные грамматические ошибки")
        
        # 6. Проверка на длину вопроса
        if len(question.split()) > 30:
            score -= 1
            issues.append("Вопрос слишком длинный (более 30 слов)")
        
        # 7. Проверка на наличие пояснения (бонус)
        if explanation and len(explanation) > 10:
            score = min(10, score + 1)  # Бонус за хорошее пояснение
        
        # 8. Проверка формата вопроса
        if not question.endswith('?'):
            score -= 1
            issues.append("Вопрос должен заканчиваться знаком вопроса")
        
        return max(1, score), issues
    
    def _is_ambiguous(self, question: str) -> bool:
        """Проверить на неоднозначность"""
        question_lower = question.lower()
        return any(word in question_lower for word in self.ambiguous_words)
    
    def _is_vague_answer(self, answer: str) -> bool:
        """Проверить на конкретность ответа"""
        # Ответ считается неконкретным, если он:
        # - Очень короткий (менее 2 символов)
        # - Не содержит ни цифр, ни заглавных букв (имена собственные)
        if len(answer) < 2:
            return True
        
        has_number = bool(re.search(r'\d+', answer))
        has_proper_noun = bool(re.search(r'[А-ЯЁ]', answer))
        
        return not (has_number or has_proper_noun or len(answer.split()) > 1)
    
    def _is_subjective(self, question: str) -> bool:
        """Проверить на субъективность"""
        question_lower = question.lower()
        return any(word in question_lower for word in self.subjective_words)
    
    def _has_grammar_issues(self, question: str) -> bool:
        """Простая проверка на грамматические ошибки"""
        # Проверка на повторяющиеся слова подряд
        words = question.lower().split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1] and len(words[i]) > 2:
                return True
        
        # Проверка на двойные пробелы
        if '  ' in question:
            return True
        
        return False
    
    def _needs_date_verification(self, question: str) -> bool:
        """Проверить, нужна ли проверка актуальности"""
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in self.date_indicators)
    
    def validate_batch(self, questions: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Проверить пакет вопросов
        Возвращает: (качественные вопросы, отклоненные вопросы)
        """
        good_questions = []
        rejected_questions = []
        
        for question in questions:
            score, issues = self.check_question_quality(question)
            
            if score >= 7:
                good_questions.append(question)
            else:
                question['quality_score'] = score
                question['quality_issues'] = issues
                rejected_questions.append(question)
        
        return good_questions, rejected_questions


# Функция для быстрой проверки одного вопроса
def quick_check(question_text: str, answer_text: str) -> Tuple[bool, str]:
    """
    Быстрая проверка вопроса
    Возвращает: (прошел проверку, причина отклонения)
    """
    checker = QualityChecker()
    
    question_data = {
        'question': question_text,
        'answer': answer_text
    }
    
    score, issues = checker.check_question_quality(question_data)
    
    if score >= 7:
        return True, "OK"
    else:
        return False, "; ".join(issues)