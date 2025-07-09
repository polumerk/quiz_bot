"""
Configuration settings for Quiz Bot
"""

import os
from typing import Optional


class Config:
    """Configuration class with environment variable support"""
    
    # Telegram Bot Configuration
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
    
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
    
    # Replit specific - updated for modern Replit
    REPL_SLUG: Optional[str] = os.getenv('REPL_SLUG')
    REPL_OWNER: Optional[str] = os.getenv('REPL_OWNER') 
    REPLIT_URL: Optional[str] = os.getenv('REPLIT_URL')  # Modern Replit provides this directly
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    DEBUG_MODE: bool = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    # Deployment mode configuration
    DEPLOYMENT_MODE: str = os.getenv('DEPLOYMENT_MODE', 'auto')  # auto, webhook, polling
    
    @classmethod
    def should_use_webhook(cls) -> bool:
        """Determine if webhook should be used based on environment"""
        # Explicit polling mode
        if cls.DEPLOYMENT_MODE.lower() == 'polling':
            return False
            
        # Explicit webhook mode
        if cls.DEPLOYMENT_MODE.lower() == 'webhook':
            return True
            
        # Auto mode: use webhook if URL is configured
        if cls.DEPLOYMENT_MODE.lower() == 'auto':
            # Check if webhook URL is explicitly set
            if cls.WEBHOOK_URL:
                return True
                
            # Check if running in Replit with available URL
            if cls.is_replit_environment() and cls.get_replit_webhook_url():
                return True
                
            # Default to polling for safety
            return False
            
        # Unknown mode, default to polling
        return False
    
    @classmethod
    def get_deployment_info(cls) -> str:
        """Get deployment mode information for logging"""
        mode = cls.DEPLOYMENT_MODE.lower()
        
        if mode == 'polling':
            return "📡 Polling mode (explicit)"
        elif mode == 'webhook':
            return "🌐 Webhook mode (explicit)"
        elif mode == 'auto':
            if cls.should_use_webhook():
                url = cls.WEBHOOK_URL or cls.get_replit_webhook_url()
                return f"🌐 Webhook mode (auto-detected: {url})"
            else:
                return "📡 Polling mode (auto-detected, no webhook URL)"
        else:
            return f"📡 Polling mode (unknown DEPLOYMENT_MODE: {mode})"
    
    @classmethod
    def load_openai_key(cls) -> str:
        """Load OpenAI API key from environment or file (for backward compatibility)"""
        if cls.OPENAI_API_KEY:
            return cls.OPENAI_API_KEY
            
        # Try environment variable first (secure)
        key = os.getenv('OPENAI_API_KEY')
        if key:
            cls.OPENAI_API_KEY = key
            return key
        
        # Fallback to file (for backward compatibility)
        try:
            with open('openai_key.txt', 'r', encoding='utf-8') as f:
                key = f.read().strip()
                cls.OPENAI_API_KEY = key
                return key
        except FileNotFoundError:
            pass
            
        raise ValueError(
            "❌ OpenAI API key not found! Please set it in Replit Secrets:\n"
            "1. 🔒 Open Secrets tab in Replit\n"
            "2. ➕ Add new secret: OPENAI_API_KEY = your_openai_key\n"
            "3. 🔄 Restart the bot\n\n"
            "Alternative: create openai_key.txt file (less secure)"
        )
    
    @classmethod
    def is_replit_environment(cls) -> bool:
        """Check if running in Replit environment"""
        # Modern check: REPLIT_URL or legacy check
        return (cls.REPLIT_URL is not None or 
                (cls.REPL_SLUG is not None and cls.REPL_OWNER is not None) or
                os.getenv('REPLIT_DEV_DOMAIN') is not None)
    
    @classmethod
    def get_replit_webhook_url(cls) -> Optional[str]:
        """Get webhook URL for Replit deployment"""
        if not cls.is_replit_environment():
            return None
            
        # Try modern REPLIT_URL first
        if cls.REPLIT_URL:
            # Remove trailing slash if present
            url = cls.REPLIT_URL.rstrip('/')
            # Ensure https
            if not url.startswith('http'):
                url = f"https://{url}"
            return url
            
        # Try REPLIT_DEV_DOMAIN (another modern variable)
        dev_domain = os.getenv('REPLIT_DEV_DOMAIN')
        if dev_domain:
            return f"https://{dev_domain}"
            
        # Fallback to legacy format
        if cls.REPL_SLUG and cls.REPL_OWNER:
            return f"https://{cls.REPL_SLUG}.{cls.REPL_OWNER}.repl.co"
            
        return None


# Global config instance
config = Config()