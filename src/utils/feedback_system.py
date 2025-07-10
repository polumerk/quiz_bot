"""
Система обратной связи для Quiz Bot 2.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

class FeedbackSystem:
    """Класс для управления обратной связью пользователей"""
    
    def __init__(self, data_file: str = "feedback_data.json"):
        self.data_file = data_file
        self.question_ratings = defaultdict(list)
        self.improvement_suggestions = []
        self.question_complaints = defaultdict(list)
        self.user_preferences = defaultdict(dict)
        self.load_data()
    
    def load_data(self):
        """Загрузить данные обратной связи из файла"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.question_ratings = defaultdict(list, data.get('question_ratings', {}))
                    self.improvement_suggestions = data.get('improvement_suggestions', [])
                    self.question_complaints = defaultdict(list, data.get('question_complaints', {}))
                    self.user_preferences = defaultdict(dict, data.get('user_preferences', {}))
            except Exception as e:
                print(f"Ошибка загрузки обратной связи: {e}")
    
    def save_data(self):
        """Сохранить данные обратной связи в файл"""
        try:
            data_to_save = {
                'question_ratings': dict(self.question_ratings),
                'improvement_suggestions': self.improvement_suggestions,
                'question_complaints': dict(self.question_complaints),
                'user_preferences': dict(self.user_preferences)
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения обратной связи: {e}")
    
    def rate_question(self, question_id: str, user_id: int, rating: int, comment: str = ""):
        """Оценить вопрос пользователем"""
        if not 1 <= rating <= 5:
            raise ValueError("Рейтинг должен быть от 1 до 5")
        
        rating_data = {
            'user_id': user_id,
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        }
        
        self.question_ratings[question_id].append(rating_data)
        self.save_data()
    
    def get_question_average_rating(self, question_id: str) -> float:
        """Получить среднюю оценку вопроса"""
        ratings = self.question_ratings.get(question_id, [])
        if not ratings:
            return 0.0
        
        total_rating = sum(r['rating'] for r in ratings)
        return round(total_rating / len(ratings), 2)
    
    def get_question_rating_count(self, question_id: str) -> int:
        """Получить количество оценок для вопроса"""
        return len(self.question_ratings.get(question_id, []))
    
    def get_question_rating_distribution(self, question_id: str) -> Dict[int, int]:
        """Получить распределение оценок для вопроса"""
        ratings = self.question_ratings.get(question_id, [])
        distribution = defaultdict(int)
        
        for rating_data in ratings:
            distribution[rating_data['rating']] += 1
        
        return dict(distribution)
    
    def submit_complaint(self, question_id: str, user_id: int, complaint_type: str, description: str):
        """Отправить жалобу на вопрос"""
        complaint_data = {
            'user_id': user_id,
            'complaint_type': complaint_type,  # 'ambiguous', 'incorrect', 'inappropriate', 'other'
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        
        self.question_complaints[question_id].append(complaint_data)
        self.save_data()
    
    def get_question_complaints(self, question_id: str) -> List[Dict]:
        """Получить жалобы на вопрос"""
        return self.question_complaints.get(question_id, [])
    
    def suggest_improvement(self, user_id: int, suggestion: str, category: str = "general"):
        """Предложить улучшение"""
        improvement_data = {
            'user_id': user_id,
            'suggestion': suggestion,
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'  # pending, approved, rejected
        }
        
        self.improvement_suggestions.append(improvement_data)
        self.save_data()
    
    def get_pending_suggestions(self) -> List[Dict]:
        """Получить ожидающие рассмотрения предложения"""
        return [s for s in self.improvement_suggestions if s['status'] == 'pending']
    
    def approve_suggestion(self, suggestion_index: int):
        """Одобрить предложение"""
        if 0 <= suggestion_index < len(self.improvement_suggestions):
            self.improvement_suggestions[suggestion_index]['status'] = 'approved'
            self.save_data()
    
    def reject_suggestion(self, suggestion_index: int, reason: str = ""):
        """Отклонить предложение"""
        if 0 <= suggestion_index < len(self.improvement_suggestions):
            self.improvement_suggestions[suggestion_index]['status'] = 'rejected'
            self.improvement_suggestions[suggestion_index]['rejection_reason'] = reason
            self.save_data()
    
    def set_user_preference(self, user_id: int, preference_type: str, value: Any):
        """Установить предпочтение пользователя"""
        self.user_preferences[user_id][preference_type] = value
        self.save_data()
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """Получить предпочтения пользователя"""
        return self.user_preferences.get(user_id, {})
    
    def suggest_improvements(self) -> List[str]:
        """Получить предложения по улучшению на основе feedback"""
        suggestions = []
        
        # Анализ низкооцененных вопросов
        low_rated_questions = []
        for question_id, ratings in self.question_ratings.items():
            avg_rating = self.get_question_average_rating(question_id)
            if avg_rating < 3.0 and len(ratings) >= 3:  # Минимум 3 оценки
                low_rated_questions.append((question_id, avg_rating))
        
        # Сортируем по средней оценке
        low_rated_questions.sort(key=lambda x: x[1])
        
        for question_id, avg_rating in low_rated_questions[:10]:  # Топ-10 худших
            suggestions.append(f"Вопрос {question_id} получил низкую оценку ({avg_rating:.1f}) - пересмотреть")
        
        # Анализ жалоб
        complaint_types = defaultdict(int)
        for complaints in self.question_complaints.values():
            for complaint in complaints:
                complaint_types[complaint['complaint_type']] += 1
        
        if complaint_types:
            most_common_complaint = max(complaint_types.items(), key=lambda x: x[1])
            suggestions.append(f"Частая жалоба: {most_common_complaint[0]} ({most_common_complaint[1]} раз)")
        
        return suggestions
    
    def get_feedback_summary(self) -> Dict:
        """Получить сводку обратной связи"""
        total_ratings = sum(len(ratings) for ratings in self.question_ratings.values())
        total_complaints = sum(len(complaints) for complaints in self.question_complaints.values())
        total_suggestions = len([s for s in self.improvement_suggestions if s['status'] == 'pending'])
        
        # Средняя оценка по всем вопросам
        all_ratings = []
        for ratings in self.question_ratings.values():
            all_ratings.extend([r['rating'] for r in ratings])
        
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        
        # Распределение оценок
        rating_distribution = defaultdict(int)
        for rating in all_ratings:
            rating_distribution[rating] += 1
        
        return {
            "total_ratings": total_ratings,
            "total_complaints": total_complaints,
            "pending_suggestions": total_suggestions,
            "average_rating": round(avg_rating, 2),
            "rating_distribution": dict(rating_distribution),
            "rated_questions": len(self.question_ratings),
            "complained_questions": len(self.question_complaints)
        }
    
    def get_low_quality_questions(self, threshold: float = 3.0, min_ratings: int = 3) -> List[Dict]:
        """Получить вопросы низкого качества"""
        low_quality = []
        
        for question_id, ratings in self.question_ratings.items():
            if len(ratings) >= min_ratings:
                avg_rating = self.get_question_average_rating(question_id)
                if avg_rating < threshold:
                    complaints = self.get_question_complaints(question_id)
                    low_quality.append({
                        'question_id': question_id,
                        'average_rating': avg_rating,
                        'rating_count': len(ratings),
                        'complaint_count': len(complaints),
                        'recent_ratings': ratings[-5:]  # Последние 5 оценок
                    })
        
        # Сортируем по средней оценке
        low_quality.sort(key=lambda x: x['average_rating'])
        return low_quality
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Очистить старые данные обратной связи"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Очищаем старые оценки
        for question_id in list(self.question_ratings.keys()):
            self.question_ratings[question_id] = [
                r for r in self.question_ratings[question_id]
                if datetime.fromisoformat(r['timestamp']) > cutoff_date
            ]
            if not self.question_ratings[question_id]:
                del self.question_ratings[question_id]
        
        # Очищаем старые жалобы
        for question_id in list(self.question_complaints.keys()):
            self.question_complaints[question_id] = [
                c for c in self.question_complaints[question_id]
                if datetime.fromisoformat(c['timestamp']) > cutoff_date
            ]
            if not self.question_complaints[question_id]:
                del self.question_complaints[question_id]
        
        # Очищаем старые предложения (кроме одобренных)
        self.improvement_suggestions = [
            s for s in self.improvement_suggestions
            if s['status'] == 'approved' or datetime.fromisoformat(s['timestamp']) > cutoff_date
        ]
        
        self.save_data()