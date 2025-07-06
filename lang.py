import random

LANGUAGES = {
    'ru': {
        'welcome': 'Добро пожаловать в квиз!',
        'choose_mode': 'Выберите режим игры:',
        'team_mode': 'Командный',
        'individual_mode': 'Каждый сам за себя',
        'choose_difficulty': 'Выберите уровень сложности:',
        'easy': 'Легкий',
        'medium': 'Средний',
        'hard': 'Сложный',
        'choose_rounds': 'Выберите количество раундов:',
        'choose_questions': 'Выберите количество вопросов в каждом раунде:',
        'choose_time': 'Выберите время на вопрос:',
        'registration_done': 'Регистрация завершена!',
        'generating_questions': 'Генерирую вопросы...',
        'stat': 'Статистика',
        'news': 'История изменений',
        'answer': 'Ответить',
        'next_round': 'Готовы к следующему раунду? Напишите "/next"',
        'quiz_finished': 'Квиз завершён! Спасибо за игру!',
        'congrats_winner': 'Поздравляем победителя:',
        'questions_in_round': 'Вопросов в раунде:',
        'time_per_question': 'Время на ответ:',
        'minutes': 'мин.',
        'answer_accepted': '✅ Ответ принят!',
        'time_is_up': '⏰ Время на обсуждение истекло!',
        'no_answer': 'Ответ не получен, вопрос пропущен.',
        'can_answer_no_bonus': 'Можно отвечать, но без бонуса за скорость.',
        'final_rating': 'Финальный рейтинг:',
        'top_players': 'Топ-5 игроков по победам:',
        'top_scores': 'Топ-5 игроков по очкам:',
        'top_themes': 'Топ-5 тем:',
        'total_games': 'Всего сыграно игр:',
        'emoji_welcome': ['👋', '🎉', '🤖', '🧠'],
        'emoji_player': ['🦁', '🐯', '🐻', '🐼', '🐨', '🐸', '🐵', '🦊', '🐧', '🐤', '🐺', '🦄', '🐲', '🐙', '🦉', '🦋', '🐞', '🐝', '🦖', '🦕'],
        'emoji_leader': ['🥇', '🥈', '🥉'],
        'feedback_good': ['Молодец!', 'Отлично!', 'Супер!', 'Так держать!', 'Блестяще!'],
        'feedback_bad': ['Почти!', 'Не сдавайся!', 'В следующий раз получится!', 'Попробуй ещё!', 'Не унывай!'],
    },
    'en': {
        'welcome': 'Welcome to the quiz!',
        'choose_mode': 'Choose game mode:',
        'team_mode': 'Team',
        'individual_mode': 'Free for all',
        'choose_difficulty': 'Choose difficulty:',
        'easy': 'Easy',
        'medium': 'Medium',
        'hard': 'Hard',
        'choose_rounds': 'Choose number of rounds:',
        'choose_questions': 'Choose number of questions per round:',
        'choose_time': 'Choose time per question:',
        'registration_done': 'Registration completed!',
        'generating_questions': 'Generating questions...',
        'stat': 'Statistics',
        'news': 'Changelog',
        'answer': 'Answer',
        'next_round': 'Ready for the next round? Type "/next"',
        'quiz_finished': 'Quiz finished! Thanks for playing!',
        'congrats_winner': 'Congratulations to the winner:',
        'questions_in_round': 'Questions per round:',
        'time_per_question': 'Time per question:',
        'minutes': 'min.',
        'answer_accepted': '✅ Answer accepted!',
        'time_is_up': '⏰ Time is up!',
        'no_answer': 'No answer received, question skipped.',
        'can_answer_no_bonus': 'You can answer, but no speed bonus.',
        'final_rating': 'Final rating:',
        'top_players': 'Top-5 players by wins:',
        'top_scores': 'Top-5 players by score:',
        'top_themes': 'Top-5 themes:',
        'total_games': 'Total games played:',
        'emoji_welcome': ['👋', '🎉', '🤖', '🧠'],
        'emoji_player': ['🦁', '🐯', '🐻', '🐼', '🐨', '🐸', '🐵', '🦊', '🐧', '🐤', '🐺', '🦄', '🐲', '🐙', '🦉', '🦋', '🐞', '🐝', '🦖', '🦕'],
        'emoji_leader': ['🥇', '🥈', '🥉'],
        'feedback_good': ['Good job!', 'Excellent!', 'Super!', 'Keep it up!', 'Brilliant!'],
        'feedback_bad': ['Almost!', 'Don’t give up!', 'You’ll get it next time!', 'Try again!', 'Don’t be sad!'],
    }
}

chat_languages = {}

def set_language(chat_id, lang_code):
    chat_languages[chat_id] = lang_code

def get_language(chat_id):
    return chat_languages.get(chat_id, 'ru')

def get_text(key, chat_id=None, lang=None):
    if lang is None and chat_id is not None:
        lang = get_language(chat_id)
    if lang is None:
        lang = 'ru'
    return LANGUAGES.get(lang, LANGUAGES['ru']).get(key, key)

def get_emoji(key, chat_id=None, lang=None):
    if lang is None and chat_id is not None:
        lang = get_language(chat_id)
    if lang is None:
        lang = 'ru'
    return random.choice(LANGUAGES.get(lang, LANGUAGES['ru']).get(key, [])) 