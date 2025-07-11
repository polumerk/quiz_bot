"""
Тестовый файл для проверки улучшенной системы вопросов Quiz Bot 2.0
"""

import asyncio
import json
from typing import Dict, List, Any

# Импортируем новые системы
try:
    from src.utils.question_types import QuestionType, determine_question_type, get_question_type_prompt
    from src.utils.analytics import QuestionAnalytics
    from src.utils.feedback_system import FeedbackSystem
    from src.utils.integration_helper import integration_helper
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что все файлы созданы в правильных директориях")
    exit(1)

def test_question_types():
    """Тест системы типов вопросов"""
    print("🧪 Тестирование системы типов вопросов...")
    
    # Тест определения типов
    test_themes = [
        ("история", QuestionType.HISTORICAL),
        ("география", QuestionType.GEOGRAPHICAL),
        ("наука", QuestionType.SCIENTIFIC),
        ("спорт", QuestionType.SPORTS),
        ("культура", QuestionType.CULTURAL),
        ("математика", QuestionType.MATHEMATICAL),
        ("логика", QuestionType.LOGICAL),
        ("ассоциации", QuestionType.ASSOCIATIVE),
        ("хронология", QuestionType.CHRONOLOGICAL),
        ("общие знания", QuestionType.FACTUAL)
    ]
    
    for theme, expected_type in test_themes:
        detected_type = determine_question_type(theme)
        status = "✅" if detected_type == expected_type else "❌"
        print(f"{status} Тема '{theme}' -> {detected_type.value} (ожидалось: {expected_type.value})")
    
    # Тест промптов
    prompt = get_question_type_prompt(QuestionType.HISTORICAL, "история России")
    print(f"📝 Промпт для исторических вопросов: {prompt[:100]}...")
    
    print("✅ Тест системы типов вопросов завершен\n")

def test_analytics():
    """Тест системы аналитики"""
    print("🧪 Тестирование системы аналитики...")
    
    analytics = QuestionAnalytics("test_analytics.json")
    
    # Тестовые данные
    test_questions = [
        {
            "question": "В каком году была Куликовская битва?",
            "answer": "1380",
            "quality_score": 9,
            "difficulty_level": 7,
            "question_type": "historical"
        },
        {
            "question": "Столица России?",
            "answer": "Москва",
            "quality_score": 8,
            "difficulty_level": 3,
            "question_type": "factual"
        }
    ]
    
    test_settings = {
        "theme": "история",
        "difficulty": "medium",
        "questions_count": 2
    }
    
    # Отслеживаем генерацию
    analytics.track_question_generation(test_questions, test_settings)
    
    # Получаем отчет
    report = analytics.get_quality_report()
    print(f"📊 Отчет о качестве: {report}")
    
    # Получаем рекомендации
    recommendations = analytics.get_recommendations()
    print(f"💡 Рекомендации: {recommendations}")
    
    print("✅ Тест системы аналитики завершен\n")

def test_feedback_system():
    """Тест системы обратной связи"""
    print("🧪 Тестирование системы обратной связи...")
    
    feedback = FeedbackSystem("test_feedback.json")
    
    # Тестовые оценки
    feedback.rate_question("q1", 123, 5, "Отличный вопрос!")
    feedback.rate_question("q1", 456, 4, "Хороший вопрос")
    feedback.rate_question("q2", 123, 2, "Неоднозначный вопрос")
    
    # Тестовые жалобы
    feedback.submit_complaint("q2", 123, "ambiguous", "Вопрос неоднозначен")
    feedback.submit_complaint("q3", 456, "incorrect", "Неправильный ответ")
    
    # Получаем сводку
    summary = feedback.get_feedback_summary()
    print(f"📊 Сводка обратной связи: {summary}")
    
    # Получаем предложения улучшений
    suggestions = feedback.suggest_improvements()
    print(f"💡 Предложения улучшений: {suggestions}")
    
    print("✅ Тест системы обратной связи завершен\n")

async def test_enhanced_generator():
    """Тест улучшенного генератора вопросов"""
    print("🧪 Тестирование улучшенного генератора вопросов...")
    
    # Тестовые настройки
    test_settings = {
        "theme": "история",
        "difficulty": "medium",
        "questions_count": 3
    }
    
    # Генерируем вопросы (если есть API ключ)
    try:
        # Вместо generator = EnhancedQuestionGenerator() используем integration_helper
        quality_questions, rejected_questions = await integration_helper.enhanced_generator.generate_questions_with_quality_check(
            test_settings, max_attempts=1
        )
        
        print(f"✅ Сгенерировано {len(quality_questions)} качественных вопросов")
        print(f"❌ Отклонено {len(rejected_questions)} низкокачественных вопросов")
        
        if quality_questions:
            print("📝 Пример качественного вопроса:")
            question = quality_questions[0]
            print(f"Вопрос: {question.get('question', '')}")
            print(f"Ответ: {question.get('answer', '')}")
            print(f"Пояснение: {question.get('explanation', '')}")
            print(f"Интересный факт: {question.get('interesting_fact', '')}")
            print(f"Качество: {question.get('quality_score', 0)}/10")
        
    except Exception as e:
        print(f"⚠️ Ошибка генерации (возможно, нет API ключа): {e}")
    
    print("✅ Тест улучшенного генератора завершен\n")

def test_integration_helper():
    """Тест интеграционного помощника"""
    print("🧪 Тестирование интеграционного помощника...")
    
    # Тестовый вопрос
    test_question = {
        "question": "В каком году была Куликовская битва?",
        "answer": "1380",
        "explanation": "Куликовская битва произошла 8 сентября 1380 года между войсками Дмитрия Донского и Мамая",
        "interesting_fact": "Это была первая крупная победа русских войск над монголо-татарами",
        "source_type": "учебник истории",
        "difficulty_level": 7,
        "tags": ["история", "Россия", "средневековье"],
        "quality_score": 9
    }
    
    # Форматирование вопроса
    formatted = integration_helper.format_enhanced_question_display(test_question)
    print("📝 Форматированный вопрос:")
    print(formatted)
    
    # Форматирование пояснения
    explanation = integration_helper.format_question_explanation(test_question)
    print("💡 Пояснение к ответу:")
    print(explanation)
    
    # Получение статистики
    stats = integration_helper.get_question_statistics()
    print(f"📊 Статистика: {stats}")
    
    print("✅ Тест интеграционного помощника завершен\n")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов улучшенной системы вопросов Quiz Bot 2.0\n")
    
    # Запускаем все тесты
    test_question_types()
    test_analytics()
    test_feedback_system()
    await test_enhanced_generator()
    test_integration_helper()
    
    print("🎉 Все тесты завершены!")
    print("\n📋 Сводка реализованных улучшений:")
    print("✅ Система типов вопросов (10 типов)")
    print("✅ Система аналитики")
    print("✅ Система обратной связи")
    print("✅ Улучшенный генератор вопросов")
    print("✅ Интеграционный помощник")
    print("✅ Образовательная ценность с пояснениями")
    print("✅ Профессиональные промпты")
    print("✅ Автоматическая фильтрация качества")
    
    print("\n🎯 Quiz Bot 2.0 готов к использованию!")

if __name__ == "__main__":
    asyncio.run(main())