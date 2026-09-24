"""botkit — Telegram + Gemini botlari uchun umumiy kutubxona."""

from .config import Settings, load_settings, require_env
from .engine import ChatEngine
from .gemini import APIError, GeminiService, is_overloaded, media_part, text_part
from .prompts import TELEGRAM_FORMAT_RULES, load_json_instruction
from .tg import (
    build_application,
    download_bytes,
    run,
    send_reply,
    setup_logging,
    split_text,
    to_telegram_html,
)

__all__ = [
    "Settings", "load_settings", "require_env",
    "ChatEngine", "APIError", "GeminiService", "is_overloaded", "media_part", "text_part",
    "TELEGRAM_FORMAT_RULES", "load_json_instruction",
    "build_application", "download_bytes", "run", "send_reply",
    "setup_logging", "split_text", "to_telegram_html",
]
