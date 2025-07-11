"""
Система аналитики для Quiz Bot 2.0
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict, Counter

class QuestionAnalytics:
    """Класс для отслеживания статистики и аналитики вопросов"""
    
    def __init__(self, data_file: str = "analytics_data.json"):
        self.data_file = data_file
        self.stats = {
            'total_generated': 0,
            'quality_distribution': defaultdict(int),  # Распределение по качеству
            'theme_performance': defaultdict(lambda: {'total': 0, 'avg_score': 0.0}),
            'difficulty_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'question_types': defaultdict(int),
            'daily_stats': defaultdict(lambda: {'generated': 0, 'avg_quality': 0.0}),
            'rejected_questions': [],
            'user_feedback': defaultdict(list)
        }
        self.load_data()
    
    def load_data(self):
        """Загрузить данные из файла"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Преобразуем defaultdict обратно
                    for key, value in data.items():
                        if key == 'quality_distribution':
                            self.stats[key] = defaultdict(int, value)
                        elif key == 'theme_performance':
                            self.stats[key] = defaultdict(lambda: {'total': 0, 'avg_score': 0.0}, value)
                        elif key == 'difficulty_accuracy':
                            self.stats[key] = defaultdict(lambda: {'correct': 0, 'total': 0}, value)
                        elif key == 'question_types':
                            self.stats[key] = defaultdict(int, value)
                        elif key == 'daily_stats':
                            self.stats[key] = defaultdict(lambda: {'generated': 0, 'avg_quality': 0.0}, value)
                        elif key == 'user_feedback':
                            self.stats[key] = defaultdict(list, value)
                        else:
                            self.stats[key] = value
            except Exception as e:
                print(f"Ошибка загрузки аналитики: {e}")
    
    def save_data(self):
        """Сохранить данные в файл"""
        try:
            # Преобразуем defaultdict в обычные dict для сохранения
            data_to_save = {}
            for key, value in self.stats.items():
                if isinstance(value, defaultdict):
                    data_to_save[key] = dict(value)
                else:
                    data_to_save[key] = value
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения аналитики: {e}")
    
    def track_question_generation(self, questions: List[Dict], settings: Dict):
        """Отслеживать статистику генерации вопросов"""
        self.stats['total_generated'] += len(questions)
        
        today = datetime.now().strftime('%Y-%m-%d')
        self.stats['daily_stats'][today]['generated'] += len(questions)
        
        # Отслеживаем качество
        total_quality = 0
        for question in questions:
            difficulty = question.get('difficulty_level', 5)
            theme = settings.get('theme', 'general')
            question_type = question.get('question_type', 'factual')
            
            # Обновляем распределение качества
            quality_score = question.get('quality_score', 7)
            self.stats['quality_distribution'][quality_score] += 1
            
            # Обновляем статистику по темам
            self._update_theme_stats(theme, quality_score)
            
            # Обновляем статистику по типам вопросов
            self.stats['question_types'][question_type] += 1
            
            total_quality += quality_score
        
        # Обновляем среднее качество за день
        if len(questions) > 0:
            avg_quality = total_quality / len(questions)
            self.stats['daily_stats'][today]['avg_quality'] = (
                (self.stats['daily_stats'][today]['avg_quality'] * 
                 (self.stats['daily_stats'][today]['generated'] - len(questions)) + 
                 total_quality) / self.stats['daily_stats'][today]['generated']
            )
        
        self.save_data()
    
    def track_game_results(self, game_results: Dict):
        """Отслеживать результаты игры для улучшения генерации"""
        for question_result in game_results.get('questions', []):
            difficulty = question_result.get('difficulty_level', 5)
            was_correct = question_result.get('correct', False)
            
            self._update_difficulty_accuracy(difficulty, was_correct)
        
        self.save_data()
    
    def track_rejected_question(self, question: Dict, reason: str):
        """Отслеживать отклоненные вопросы"""
        rejected_data = {
            'question': question.get('question', ''),
            'theme': question.get('theme', ''),
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.stats['rejected_questions'].append(rejected_data)
        
        # Ограничиваем количество сохраненных отклоненных вопросов
        if len(self.stats['rejected_questions']) > 1000:
            self.stats['rejected_questions'] = self.stats['rejected_questions'][-500:]
        
        self.save_data()
    
    def track_user_feedback(self, question_id: str, rating: int, comment: str = ""):
        """Отслеживать обратную связь пользователей"""
        feedback_data = {
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        }
        self.stats['user_feedback'][question_id].append(feedback_data)
        self.save_data()
    
    def _update_theme_stats(self, theme: str, quality_score: int):
        """Обновить статистику по темам"""
        theme_stats = self.stats['theme_performance'][theme]
        theme_stats['total'] += 1
        
        # Обновляем среднее качество
        current_avg = theme_stats['avg_score']
        total_questions = theme_stats['total']
        new_avg = ((current_avg * (total_questions - 1)) + quality_score) / total_questions
        theme_stats['avg_score'] = new_avg
    
    def _update_difficulty_accuracy(self, difficulty: int, was_correct: bool):
        """Обновить статистику точности по сложности"""
        diff_stats = self.stats['difficulty_accuracy'][difficulty]
        diff_stats['total'] += 1
        if was_correct:
            diff_stats['correct'] += 1
    
    def get_recommendations(self) -> Dict[str, str]:
        """Получить рекомендации по улучшению генерации"""
        recommendations = {}
        
        # Анализ точности по сложности
        for difficulty, stats in self.stats['difficulty_accuracy'].items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total']
                if accuracy < 0.3:
                    recommendations[f'difficulty_{difficulty}'] = f"Слишком сложные вопросы (точность {accuracy:.1%})"
                elif accuracy > 0.9:
                    recommendations[f'difficulty_{difficulty}'] = f"Слишком простые вопросы (точность {accuracy:.1%})"
        
        # Анализ качества по темам
        for theme, stats in self.stats['theme_performance'].items():
            if stats['total'] > 10:  # Минимум вопросов для анализа
                if stats['avg_score'] < 6.0:
                    recommendations[f'theme_{theme}'] = f"Низкое качество вопросов по теме '{theme}' (средний балл {stats['avg_score']:.1f})"
        
        # Анализ отклоненных вопросов
        if len(self.stats['rejected_questions']) > 50:
            rejection_reasons = Counter(q['reason'] for q in self.stats['rejected_questions'][-100:])
            most_common_reason = rejection_reasons.most_common(1)[0]
            recommendations['rejection_rate'] = f"Частая причина отклонения: {most_common_reason[0]} ({most_common_reason[1]} раз)"
        
        return recommendations
    
    def get_quality_report(self) -> Dict:
        """Получить отчет о качестве вопросов"""
        total_questions = self.stats['total_generated']
        if total_questions == 0:
            return {"error": "Нет данных для анализа"}
        
        # Распределение качества
        quality_dist = dict(self.stats['quality_distribution'])
        avg_quality = sum(score * count for score, count in quality_dist.items()) / total_questions
        
        # Лучшие и худшие темы
        theme_performance = dict(self.stats['theme_performance'])
        if theme_performance:
            best_theme = max(theme_performance.items(), key=lambda x: x[1]['avg_score'])
            worst_theme = min(theme_performance.items(), key=lambda x: x[1]['avg_score'])
        else:
            best_theme = worst_theme = None
        
        # Статистика по типам вопросов
        question_types = dict(self.stats['question_types'])
        
        return {
            "total_questions": total_questions,
            "average_quality": round(avg_quality, 2),
            "quality_distribution": quality_dist,
            "best_theme": best_theme,
            "worst_theme": worst_theme,
            "question_types": question_types,
            "recent_rejections": len(self.stats['rejected_questions'][-50:])
        }
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Получить статистику за последние дни"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            stats = self.stats['daily_stats'][date_str]
            daily_stats.append({
                'date': date_str,
                'generated': stats['generated'],
                'avg_quality': round(stats['avg_quality'], 2)
            })
            current_date += timedelta(days=1)
        
        return daily_stats
    
    def get_user_feedback_summary(self) -> Dict:
        """Получить сводку обратной связи пользователей"""
        all_ratings = []
        for question_ratings in self.stats['user_feedback'].values():
            all_ratings.extend([r['rating'] for r in question_ratings])
        
        if not all_ratings:
            return {"error": "Нет данных обратной связи"}
        
        return {
            "total_feedback": len(all_ratings),
            "average_rating": round(sum(all_ratings) / len(all_ratings), 2),
            "rating_distribution": Counter(all_ratings)
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Очистить старые данные"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Очищаем старые отклоненные вопросы
        self.stats['rejected_questions'] = [
            q for q in self.stats['rejected_questions']
            if datetime.fromisoformat(q['timestamp']) > cutoff_date
        ]
        
        # Очищаем старые данные обратной связи
        for question_id in list(self.stats['user_feedback'].keys()):
            self.stats['user_feedback'][question_id] = [
                f for f in self.stats['user_feedback'][question_id]
                if datetime.fromisoformat(f['timestamp']) > cutoff_date
            ]
            if not self.stats['user_feedback'][question_id]:
                del self.stats['user_feedback'][question_id]
        
        self.save_data()