"""
Internationalization (i18n) module for multi-language support.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Localization:
    """Internationalization handler."""
    
    def __init__(self, locales_dir: Path = Path("locales")):
        """Initialize localization handler."""
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.user_languages: Dict[int, str] = {}
        self.default_language = "en"
        
        # Load all translations
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files."""
        try:
            for locale_file in self.locales_dir.glob("*.json"):
                locale_name = locale_file.stem
                
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[locale_name] = json.load(f)
                
                logger.info(f"Loaded translation for {locale_name}")
            
            logger.info(f"Loaded {len(self.translations)} languages")
            
        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
            # Fallback to empty dict
            self.translations = {self.default_language: {}}
    
    def get_text(self, chat_id: int, key: str, **kwargs) -> str:
        """Get translated text for user/chat."""
        user_lang = self.user_languages.get(chat_id, self.default_language)
        return self.get_text_by_lang(user_lang, key, **kwargs)
    
    def get_text_by_lang(self, lang: str, key: str, **kwargs) -> str:
        """Get translated text by language."""
        # Try requested language
        if lang in self.translations and key in self.translations[lang]:
            text = self.translations[lang][key]
        else:
            # Fallback to default language
            if self.default_language in self.translations and key in self.translations[self.default_language]:
                text = self.translations[self.default_language][key]
                logger.warning(f"Falling back to default language for key: {key}")
            else:
                # Final fallback
                text = f"[MISSING_TRANSLATION: {key}]"
                logger.error(f"Missing translation for key: {key}")
        
        # Format with kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.error(f"Failed to format text '{text}' with {kwargs}: {e}")
                text = f"[FORMAT_ERROR: {key}]"
        
        return text
    
    def set_user_language(self, chat_id: int, lang: str):
        """Set user language preference."""
        if lang in self.translations:
            self.user_languages[chat_id] = lang
            logger.info(f"Set language to {lang} for chat {chat_id}")
        else:
            logger.warning(f"Unknown language: {lang}")
    
    def get_user_language(self, chat_id: int) -> str:
        """Get user language preference."""
        return self.user_languages.get(chat_id, self.default_language)
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages."""
        return {
            "en": "English",
            "ar": "العربية"
        }
    
    def format_duration(self, seconds: int, chat_id: int) -> str:
        """Format duration in human readable format."""
        if seconds <= 0:
            return self.get_text(chat_id, "time_formats.unknown")
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return self.get_text(chat_id, "time_formats.long",
                               hours=hours, minutes=minutes, seconds=secs)
        else:
            return self.get_text(chat_id, "time_formats.short",
                               minutes=minutes, seconds=secs)
    
    def format_progress_bar(self, current: int, total: int, chat_id: int) -> str:
        """Format progress bar."""
        if total <= 0:
            return ""
        
        progress = int((current / total) * 20)  # 20 characters max
        
        config = self.translations.get(
            self.user_languages.get(chat_id, self.default_language), {}
        ).get("progress_bar", {})
        
        filled = config.get("filled", "●")
        empty = config.get("empty", "○")
        length = config.get("length", 20)
        
        bar = filled * progress + empty * (length - progress)
        percentage = int((current / total) * 100)
        
        return f"{bar} {percentage}%"
