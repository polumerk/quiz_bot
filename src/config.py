"""
Configuration settings for Quiz Bot
"""

import os
from typing import Optional


class Config:
    """Configuration class with environment variable support"""
    
    # Telegram Bot Configuration
    TELEGRAM_TOKEN: str = os.getenv(
        'TELEGRAM_TOKEN', 
        '8082065832:AAFMg57PUuHJzTt2YavoqCK5pEBYlhpVdYg'
    )
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.2
    OPENAI_MAX_TOKENS: int = 1024
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'quizbot.db')
    
    # Game Default Settings
    DEFAULT_LANGUAGE: str = 'ru'
    DEFAULT_ROUNDS: int = 2
    DEFAULT_QUESTIONS_PER_ROUND: int = 2
    DEFAULT_TIME_PER_QUESTION: int = 300
    DEFAULT_DIFFICULTY: str = 'medium'
    
    # Webhook Configuration (for deployment)
    WEBHOOK_URL: Optional[str] = os.getenv('WEBHOOK_URL')
    WEBHOOK_PORT: int = int(os.getenv('WEBHOOK_PORT', '443'))
    WEBHOOK_LISTEN: str = os.getenv('WEBHOOK_LISTEN', '0.0.0.0')
    
    # Replit specific
    REPL_SLUG: Optional[str] = os.getenv('REPL_SLUG')
    REPL_OWNER: Optional[str] = os.getenv('REPL_OWNER')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def load_openai_key(cls) -> str:
        """Load OpenAI API key from file or environment"""
        if cls.OPENAI_API_KEY:
            return cls.OPENAI_API_KEY
            
        # Try to load from file
        try:
            with open('openai_key.txt', 'r', encoding='utf-8') as f:
                key = f.read().strip()
                cls.OPENAI_API_KEY = key
                return key
        except FileNotFoundError:
            pass
        
        # Try environment variable
        key = os.getenv('OPENAI_API_KEY')
        if key:
            cls.OPENAI_API_KEY = key
            return key
            
        raise ValueError(
            "OpenAI API key not found. Please provide it via:\n"
            "1. openai_key.txt file\n"
            "2. OPENAI_API_KEY environment variable\n"
            "3. Config.OPENAI_API_KEY class attribute"
        )
    
    @classmethod
    def is_replit_environment(cls) -> bool:
        """Check if running in Replit environment"""
        return cls.REPL_SLUG is not None and cls.REPL_OWNER is not None
    
    @classmethod
    def get_replit_webhook_url(cls) -> Optional[str]:
        """Get webhook URL for Replit deployment"""
        if not cls.is_replit_environment():
            return None
        return f"https://{cls.REPL_SLUG}.{cls.REPL_OWNER}.repl.co"


# Global config instance
config = Config()