"""
Помощник для интеграции улучшенной системы вопросов в существующий код
"""

from typing import Dict, List, Any, Tuple, Optional
import asyncio
import traceback

# Импортируем новые системы
try:
    from .enhanced_questions import EnhancedQuestionGenerator
    try:
        from .quality_checker import QualityChecker
    except ImportError:
        QualityChecker = None
    try:
        from .analytics import QuestionAnalytics
    except ImportError:
        QuestionAnalytics = None
    try:
        from .feedback_system import FeedbackSystem
    except ImportError:
        FeedbackSystem = None
except ImportError:
    # Если модули еще не созданы, используем заглушки
    class EnhancedQuestionGenerator:
        def __init__(self):
            pass
        async def generate_questions_with_quality_check(self, *args, **kwargs):
            return [], []
    QualityChecker = None
    QuestionAnalytics = None
    FeedbackSystem = None

class IntegrationHelper:
    """Помощник для интеграции новых систем в существующий код"""
    
    def __init__(self):
        self.enhanced_generator = EnhancedQuestionGenerator()
        self.quality_checker = QualityChecker() if QualityChecker else None
        self.analytics = QuestionAnalytics() if QuestionAnalytics else None
        self.feedback_system = FeedbackSystem() if FeedbackSystem else None
    
    async def generate_enhanced_questions(
        self, 
        theme: str, 
        round_num: int, 
        chat_id: int, 
        get_difficulty, 
        get_questions_per_round
    ) -> List[Dict[str, Any]]:
        print('[DEBUG] [integration_helper] generate_enhanced_questions: вход')
        settings = {
            'theme': theme,
            'difficulty': get_difficulty(chat_id),
            'questions_count': get_questions_per_round(chat_id),
            'round_num': round_num,
            'chat_id': chat_id
        }
        print('[DEBUG] [integration_helper] settings:', settings)
        print('[DEBUG] [integration_helper] type(enhanced_generator):', type(self.enhanced_generator))
        print('[DEBUG] [integration_helper] repr(enhanced_generator):', repr(self.enhanced_generator))
        try:
            print('[DEBUG] [integration_helper] call generate_questions_with_quality_check')
            quality_questions, rejected_questions = await self.enhanced_generator.generate_questions_with_quality_check(settings)
            print('[DEBUG] [integration_helper] got quality_questions:', quality_questions)
            print('[DEBUG] [integration_helper] got rejected_questions:', rejected_questions)
        except Exception as e:
            print('[DEBUG] [integration_helper] Exception in generate_questions_with_quality_check:', e)
            traceback.print_exc()
            return []
        if rejected_questions:
            print(f"[LOG] Отклонено {len(rejected_questions)} вопросов низкого качества")
        print('[DEBUG] [integration_helper] return quality_questions:', quality_questions)
        return quality_questions
    
    def check_single_question_quality(self, question_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Проверить качество одного вопроса"""
        if self.quality_checker:
            return self.quality_checker.check_question_quality(question_data)
        return 7, []
    
    def get_quality_analytics(self) -> Dict[str, Any]:
        """Получить аналитику качества вопросов"""
        if self.analytics:
            return self.analytics.get_quality_report()
        return {"error": "Not implemented yet"}
    
    def get_feedback_analytics(self) -> Dict[str, Any]:
        """Получить аналитику обратной связи"""
        if self.feedback_system:
            return self.feedback_system.get_feedback_summary()
        return {"error": "Not implemented yet"}
    
    def get_improvement_recommendations(self) -> Dict[str, str]:
        """Получить рекомендации по улучшению"""
        get_recommendations = getattr(self.enhanced_generator, 'get_recommendations', None)
        if callable(get_recommendations):
            result = get_recommendations()
            if isinstance(result, dict):
                return dict(result)
        return {}
    
    def rate_question(self, question_id: str, user_id: int, rating: int, comment: str = ""):
        """Оценить вопрос пользователем"""
        if self.feedback_system:
            self.feedback_system.rate_question(question_id, user_id, rating, comment)
    
    def submit_complaint(self, question_id: str, user_id: int, complaint_type: str, description: str):
        """Отправить жалобу на вопрос"""
        if self.feedback_system and hasattr(self.feedback_system, 'submit_complaint'):
            self.feedback_system.submit_complaint(question_id, user_id, complaint_type, description)
    
    def track_game_results(self, game_results: Dict[str, Any]):
        """Отслеживать результаты игры"""
        if self.analytics and hasattr(self.analytics, 'track_game_results'):
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
        quality_report = self.analytics.get_quality_report() if self.analytics else {"error": "Not implemented yet"}
        feedback_summary = self.feedback_system.get_feedback_summary() if self.feedback_system else {"error": "Not implemented yet"}
        
        return {
            "quality": quality_report,
            "feedback": feedback_summary,
            "recommendations": self.get_improvement_recommendations()
        }
    
    def cleanup_old_data(self):
        """Очистить старые данные"""
        if self.analytics and hasattr(self.analytics, 'cleanup_old_data'):
            self.analytics.cleanup_old_data()
        if self.feedback_system and hasattr(self.feedback_system, 'cleanup_old_data'):
            self.feedback_system.cleanup_old_data()

# Глобальный экземпляр для использования в других модулях
integration_helper = IntegrationHelper()