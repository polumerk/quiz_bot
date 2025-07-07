"""
Error handling utilities
"""

import logging
import traceback
from typing import Optional, Callable, Any, TypeVar, Awaitable, Coroutine
from functools import wraps

from ..models.types import ChatID


# Set up logger
logger = logging.getLogger(__name__)

F = TypeVar('F')


def log_error(error: Exception, context: str = "", chat_id: Optional[ChatID] = None) -> None:
    """Log error with context information"""
    error_msg = f"Error in {context}: {type(error).__name__}: {error}"
    if chat_id:
        error_msg += f" (Chat ID: {chat_id})"
    
    logger.error(error_msg)
    logger.debug(traceback.format_exc())


def handle_error(
    error: Exception, 
    context: str = "", 
    chat_id: Optional[ChatID] = None,
    user_message: str = "Произошла ошибка. Попробуйте позже."
) -> str:
    """Handle error and return user-friendly message"""
    log_error(error, context, chat_id)
    return user_message


def safe_async_call(context: str = ""):
    """Decorator for safe async function calls with error handling"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Try to extract chat_id from args
                chat_id = None
                for arg in args:
                    if hasattr(arg, 'effective_chat') and arg.effective_chat:
                        chat_id = ChatID(arg.effective_chat.id)
                        break
                    elif hasattr(arg, 'message') and arg.message and arg.message.chat:
                        chat_id = ChatID(arg.message.chat.id)
                        break
                
                log_error(e, context or func.__name__, chat_id)
                
                # Try to send error message to user if possible
                try:
                    if hasattr(args[0], 'message') and hasattr(args[0].message, 'reply_text'):
                        await args[0].message.reply_text(
                            "😕 Произошла ошибка. Попробуйте позже или обратитесь к администратору."
                        )
                    elif hasattr(args[1], 'bot') and chat_id:
                        await args[1].bot.send_message(
                            chat_id, 
                            "😕 Произошла ошибка. Попробуйте позже или обратитесь к администратору."
                        )
                except Exception as send_error:
                    log_error(send_error, "sending error message")
                
                # Re-raise critical errors
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                
        return wrapper
    return decorator


def safe_call(context: str = "", default_return: Any = None):
    """Decorator for safe synchronous function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(e, context or func.__name__)
                return default_return
        return wrapper
    return decorator


class QuizBotError(Exception):
    """Base exception for quiz bot errors"""
    def __init__(self, message: str, chat_id: Optional[ChatID] = None):
        super().__init__(message)
        self.chat_id = chat_id


class GameStateError(QuizBotError):
    """Errors related to game state"""
    pass


class ConfigError(QuizBotError):
    """Configuration errors"""
    pass


class OpenAIError(QuizBotError):
    """OpenAI API errors"""
    pass


class DatabaseError(QuizBotError):
    """Database operation errors"""
    pass