"""
Custom message filters for telegram bot
"""

from telegram import Message
from telegram.ext import filters

from ..models.game_state import get_game_state
from ..models.types import ChatID


class ThemeStageFilter(filters.MessageFilter):
    """Filter for theme input stage"""
    
    def filter(self, message: Message) -> bool:
        """Check if chat is waiting for theme input"""
        if not message or not message.chat:
            return False
            
        chat_id = ChatID(message.chat.id)
        game_state = get_game_state(chat_id)
        return game_state.awaiting_theme


class AnswerStageFilter(filters.MessageFilter):
    """Filter for answer input stage"""
    
    def filter(self, message: Message) -> bool:
        """Check if chat is waiting for answer input"""
        if not message or not message.chat:
            return False
            
        chat_id = ChatID(message.chat.id)
        game_state = get_game_state(chat_id)
        return game_state.awaiting_text_answer


class LanguageStageFilter(filters.MessageFilter):
    """Filter for language selection stage"""
    
    def filter(self, message: Message) -> bool:
        """Check if chat is waiting for language selection"""
        if not message or not message.chat:
            return False
            
        chat_id = ChatID(message.chat.id)
        game_state = get_game_state(chat_id)
        return game_state.awaiting_language


# Filter instances for use in handlers
THEME_STAGE_FILTER = ThemeStageFilter()
ANSWER_STAGE_FILTER = AnswerStageFilter()
LANGUAGE_STAGE_FILTER = LanguageStageFilter()