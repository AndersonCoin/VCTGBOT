"""
Configuration management with environment variables and validation.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    """Database configuration."""
    backend: str = Field(default="memory", description="Storage backend: memory, tinydb, sqlite")
    
    @validator('backend')
    def validate_backend(cls, v):
        allowed = ['memory', 'tinydb', 'sqlite']
        if v not in allowed:
            raise ValueError(f'Backend must be one of {allowed}')
        return v


class BotConfig(BaseModel):
    """Bot configuration."""
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API Hash")
    bot_token: str = Field(..., description="Bot Token")
    session_string: str = Field(..., description="Assistant session string")
    assistant_username: str = Field(..., description="Assistant username")
    
    @validator('api_id')
    def validate_api_id(cls, v):
        if not isinstance(v, int) or v <= 0:
            raise ValueError('API_ID must be a positive integer')
        return v
    
    @validator('bot_token')
    def validate_bot_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError('BOT_TOKEN must be provided and valid')
        return v


class AppConfig(BaseModel):
    """Application configuration."""
    download_dir: Path = Field(default="./downloads", description="Download directory")
    log_level: str = Field(default="INFO", description="Logging level")
    port: int = Field(default=8080, description="Health check server port")
    
    @validator('download_dir')
    def validate_download_dir(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path.absolute()
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of {allowed}')
        return v.upper()
    
    @validator('port')
    def validate_port(cls, v):
        if not isinstance(v, int) or v <= 0 or v > 65535:
            raise ValueError('PORT must be a valid port number (1-65535)')
        return v


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.bot = BotConfig(
            api_id=int(os.getenv('API_ID', 0)),
            api_hash=os.getenv('API_HASH', ''),
            bot_token=os.getenv('BOT_TOKEN', ''),
            session_string=os.getenv('SESSION_STRING', ''),
            assistant_username=os.getenv('ASSISTANT_USERNAME', '')
        )
        self.app = AppConfig(
            download_dir=os.getenv('DOWNLOAD_DIR', './downloads'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            port=int(os.getenv('PORT', 8080))
        )
        self.database = DatabaseConfig(
            backend=os.getenv('STATE_BACKEND', 'memory')
        )
    
    def validate(self) -> None:
        """Validate all configuration values."""
        try:
            self.bot.api_id = int(os.getenv('API_ID', 0))
            if not self.bot.api_id:
                raise ValueError("API_ID environment variable is required")
            
            if not os.getenv('API_HASH'):
                raise ValueError("API_HASH environment variable is required")
            
            if not os.getenv('BOT_TOKEN'):
                raise ValueError("BOT_TOKEN environment variable is required")
            
            if not os.getenv('SESSION_STRING'):
                raise ValueError("SESSION_STRING environment variable is required")
            
            if not os.getenv('ASSISTANT_USERNAME'):
                raise ValueError("ASSISTANT_USERNAME environment variable is required")
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def __str__(self) -> str:
        return f"""
Configuration:
  Bot API ID: {self.bot.api_id}
  Assistant Username: {self.bot.assistant_username}
  Download Directory: {self.app.download_dir}
  Log Level: {self.app.log_level}
  Port: {self.app.port}
  State Backend: {self.database.backend}
        """


# Global configuration instance
config = Config()
