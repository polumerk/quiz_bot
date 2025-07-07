"""
Error handling utilities
"""

import logging
import traceback
from typing import Optional, Callable, Any, TypeVar, Awaitable, Coroutine
from functools import wraps

from ..models.types import ChatID
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest


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


def safe_async_call(name: str = ""):
    """Decorator для безопасного выполнения асинхронных функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                func_name = name or func.__name__
                logger.error(f"❌ Error in {func_name}: {e}")
                # Если есть update и context, попробуем отправить сообщение об ошибке
                if len(args) >= 2:
                    update, context = args[0], args[1]
                    if hasattr(update, 'effective_chat') and update.effective_chat:
                        try:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="❌ Произошла ошибка. Попробуйте еще раз."
                            )
                        except:
                            pass
                return None
        return wrapper
    return decorator

async def safe_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> bool:
    """Безопасное удаление сообщения с обработкой ошибок"""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except BadRequest as e:
        if "message to delete not found" in str(e).lower():
            logger.debug(f"Message {message_id} already deleted or doesn't exist")
        else:
            logger.warning(f"Failed to delete message {message_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id}: {e}")
        return False


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