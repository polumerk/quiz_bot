"""
Utils package for Quiz Bot 2.0
"""

from .error_handler import (
    log_error, handle_error, safe_async_call, safe_delete_message, 
    safe_call, QuizBotError, GameStateError, ConfigError, OpenAIError, DatabaseError
)
from .filters import (
    ThemeStageFilter, AnswerStageFilter, LanguageStageFilter,
    THEME_STAGE_FILTER, ANSWER_STAGE_FILTER, LANGUAGE_STAGE_FILTER
)
from .formatters import (
    format_round_results_individual, format_round_results_team,
    format_settings_summary, format_participant_list
)

# Новые модули для улучшенной системы вопросов
try:
    from .question_types import QuestionType, determine_question_type, get_question_type_prompt
    from .integration_helper import integration_helper
except ImportError:
    # Если модули еще не созданы, создаем заглушки
    pass

__all__ = [
    # Error handling
    'log_error', 'handle_error', 'safe_async_call', 'safe_delete_message', 
    'safe_call', 'QuizBotError', 'GameStateError', 'ConfigError', 'OpenAIError', 'DatabaseError',
    
    # Filters
    'ThemeStageFilter', 'AnswerStageFilter', 'LanguageStageFilter',
    'THEME_STAGE_FILTER', 'ANSWER_STAGE_FILTER', 'LANGUAGE_STAGE_FILTER',
    
    # Formatters
    'format_round_results_individual', 'format_round_results_team',
    'format_settings_summary', 'format_participant_list',
    
    # Enhanced question system
    'QuestionType',
    'determine_question_type',
    'get_question_type_prompt',
    'integration_helper'
]