"""
Formatters for displaying game results
"""

from typing import Dict, List, Optional, Any

from ..models.types import ChatID, UserID, ScoreDict, ExplanationDict
from ..models.game_state import get_game_state
import lang


def format_round_results_individual(
    participants: Dict[UserID, str], 
    score_by_user: ScoreDict, 
    fast_bonus_by_user: ScoreDict, 
    explanations_by_user: ExplanationDict, 
    chat_id: Optional[ChatID] = None
) -> str:
    """Format results for individual game mode"""
    sorted_participants = sorted(
        participants.items(), 
        key=lambda x: (score_by_user.get(x[0], 0) + fast_bonus_by_user.get(x[0], 0)), 
        reverse=True
    )
    
    text = '🏁 Раунд завершён!\n\n'
    
    for pos, (uid, name) in enumerate(sorted_participants):
        total = score_by_user.get(uid, 0)
        bonus = fast_bonus_by_user.get(uid, 0)
        medal = lang.get_emoji('emoji_leader', chat_id) if pos < 3 else '⭐'
        text += f'{medal} {name}: {total} правильных, {bonus} бонусов (итого: {total + bonus})\n'
        
        user_explanations = explanations_by_user.get(uid, [])
        for idx, result in enumerate(user_explanations, 1):
            status = '✅' if result.get('correct') else '❌'
            explanation = result.get('explanation', '')
            correct_answer = result.get('correct_answer') or result.get('reference_answer') or ''
            
            text += f'    {status} Вопрос {idx}: {result.get("question")}\n'
            text += f'    Ответ: {result.get("answer")}\n'
            
            if correct_answer:
                text += f'    Верный ответ: {correct_answer}\n'
            text += f'    Комментарий: {explanation}\n'
        text += '\n'
    
    return text


def format_round_results_team(
    results: List[Dict[str, Any]], 
    correct: int, 
    total: int, 
    fast_bonus: int, 
    fast_time: Optional[float], 
    total_score: int, 
    total_fast_bonus: int
) -> str:
    """Format results for team game mode"""
    text = f'🏁 Раунд завершён!\nПравильных ответов: {correct} из {total}\n'
    
    if fast_bonus:
        if fast_time is not None:
            text += f'⚡ Бонус за быстрый ответ (+1)! Ответ был дан за {int(fast_time)} секунд.\n'
        else:
            text += f'⚡ Бонус за быстрый ответ (+1)!\n'
    text += '\n'
    
    for i, result in enumerate(results, 1):
        status = '✅' if result.get('correct') else '❌'
        explanation = result.get('explanation', '')
        correct_answer = result.get('correct_answer') or result.get('reference_answer') or ''
        
        text += f'{status} Вопрос {i}: {result.get("question")}\n'
        text += f'Ответ: {result.get("answer")}\n'
        
        if correct_answer:
            text += f'Верный ответ: {correct_answer}\n'
        text += f'Комментарий: {explanation}\n\n'
    
    total_points = total_score + total_fast_bonus
    text += f'⭐ Промежуточный счёт: {total_score} правильных ответов, '
    text += f'{total_fast_bonus} бонусов (итого: {total_points} баллов) за все раунды.'
    
    return text


def format_settings_summary(chat_id: ChatID) -> str:
    """Format current game settings"""
    game_state = get_game_state(chat_id)
    settings = game_state.settings
    
    if not settings:
        return "Настройки не заданы"
    
    mode_text = "Командный" if settings.mode.value == "team" else "Индивидуальный"
    difficulty_map = {"easy": "Легкий", "medium": "Средний", "hard": "Сложный"}
    difficulty_text = difficulty_map.get(settings.difficulty.value, settings.difficulty.value)
    
    text = f"🎮 Настройки игры:\n"
    text += f"• Режим: {mode_text}\n"
    text += f"• Сложность: {difficulty_text}\n"
    text += f"• Раундов: {settings.rounds}\n"
    text += f"• Вопросов в раунде: {settings.questions_per_round}\n"
    text += f"• Время на вопрос: {settings.time_per_question} сек\n"
    text += f"• Тема: {settings.theme}\n"
    
    return text


def format_participant_list(chat_id: ChatID) -> str:
    """Format list of participants"""
    game_state = get_game_state(chat_id)
    participants = game_state.participants
    
    if not participants:
        return "Нет участников"
    
    text = f"👥 Участники ({len(participants)}):\n"
    for participant in participants:
        emoji = "👑" if participant.user_id == game_state.captain_id else "👤"
        text += f"{emoji} {participant.username}\n"
    
    return text