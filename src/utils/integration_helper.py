"""
Помощник для интеграции улучшенной системы вопросов в существующий код
"""

from typing import Dict, List, Any, Tuple, Optional
import asyncio

# Импортируем новые системы
try:
    from .enhanced_questions import EnhancedQuestionGenerator
    from .quality_checker import QualityChecker
    from .analytics import QuestionAnalytics
    from .feedback_system import FeedbackSystem
except ImportError:
    # Если модули еще не созданы, используем заглушки
    class EnhancedQuestionGenerator:
        def __init__(self):
            pass
        async def generate_questions_with_quality_check(self, *args, **kwargs):
            return [], []
    
    class QualityChecker:
        def check_question_quality(self, question_data):
            return 7, []
    
    class QuestionAnalytics:
        def track_question_generation(self, questions, settings):
            pass
        def get_quality_report(self):
            return {"error": "Not implemented yet"}
    
    class FeedbackSystem:
        def rate_question(self, question_id, user_id, rating, comment):
            pass
        def get_feedback_summary(self):
            return {"error": "Not implemented yet"}

class IntegrationHelper:
    """Помощник для интеграции новых систем в существующий код"""
    
    def __init__(self):
        self.enhanced_generator = EnhancedQuestionGenerator()
        self.quality_checker = QualityChecker()
        self.analytics = QuestionAnalytics()
        self.feedback_system = FeedbackSystem()
    
    async def generate_enhanced_questions(
        self, 
        theme: str, 
        round_num: int, 
        chat_id: int, 
        get_difficulty, 
        get_questions_per_round
    ) -> List[Dict[str, Any]]:
        """
        Генерация вопросов с использованием улучшенной системы
        Возвращает только качественные вопросы
        """
        quality_questions, rejected_questions = await self.enhanced_generator.generate_questions_with_quality_check(
            theme, round_num, chat_id, get_difficulty, get_questions_per_round
        )
        
        # Логируем статистику
        if rejected_questions:
            print(f"[LOG] Отклонено {len(rejected_questions)} вопросов низкого качества")
        
        return quality_questions
    
    def check_single_question_quality(self, question_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Проверить качество одного вопроса"""
        return self.quality_checker.check_question_quality(question_data)
    
    def get_quality_analytics(self) -> Dict[str, Any]:
        """Получить аналитику качества вопросов"""
        return self.analytics.get_quality_report()
    
    def get_feedback_analytics(self) -> Dict[str, Any]:
        """Получить аналитику обратной связи"""
        return self.feedback_system.get_feedback_summary()
    
    def get_improvement_recommendations(self) -> Dict[str, str]:
        """Получить рекомендации по улучшению"""
        return self.enhanced_generator.get_recommendations()
    
    def rate_question(self, question_id: str, user_id: int, rating: int, comment: str = ""):
        """Оценить вопрос пользователем"""
        self.feedback_system.rate_question(question_id, user_id, rating, comment)
    
    def submit_complaint(self, question_id: str, user_id: int, complaint_type: str, description: str):
        """Отправить жалобу на вопрос"""
        self.feedback_system.submit_complaint(question_id, user_id, complaint_type, description)
    
    def track_game_results(self, game_results: Dict[str, Any]):
        """Отслеживать результаты игры"""
        self.analytics.track_game_results(game_results)
    
    def format_enhanced_question_display(self, question: Dict[str, Any]) -> str:
        """Форматировать вопрос для отображения с дополнительной информацией"""
        text = f"❓ {question.get('question', '')}\n\n"
        
        # Добавляем пояснение, если есть
        explanation = question.get('explanation', '')
        if explanation:
            text += f"💡 {explanation}\n\n"
        
        # Добавляем интересный факт, если есть
        interesting_fact = question.get('interesting_fact', '')
        if interesting_fact:
            text += f"🎯 {interesting_fact}\n\n"
        
        # Добавляем информацию о качестве
        quality_score = question.get('quality_score', 0)
        if quality_score > 0:
            text += f"⭐ Оценка качества: {quality_score}/10\n"
        
        # Добавляем теги, если есть
        tags = question.get('tags', [])
        if tags:
            text += f"🏷️ Теги: {', '.join(tags)}\n"
        
        return text
    
    def format_question_explanation(self, question: Dict[str, Any]) -> str:
        """Форматировать пояснение к вопросу"""
        text = ""
        
        explanation = question.get('explanation', '')
        if explanation:
            text += f"💡 {explanation}\n\n"
        
        interesting_fact = question.get('interesting_fact', '')
        if interesting_fact:
            text += f"🎯 {interesting_fact}\n\n"
        
        source_type = question.get('source_type', '')
        if source_type and source_type != 'general':
            text += f"📚 Источник: {source_type}\n"
        
        return text
    
    def get_question_statistics(self) -> Dict[str, Any]:
        """Получить статистику по вопросам"""
        quality_report = self.analytics.get_quality_report()
        feedback_summary = self.feedback_system.get_feedback_summary()
        
        return {
            "quality": quality_report,
            "feedback": feedback_summary,
            "recommendations": self.get_improvement_recommendations()
        }
    
    def cleanup_old_data(self):
        """Очистить старые данные"""
        self.analytics.cleanup_old_data()
        self.feedback_system.cleanup_old_data()

# Глобальный экземпляр для использования в других модулях
integration_helper = IntegrationHelper()