"""Umumiy sozlamalar: .env faylini o'qish va Settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def require_env(name: str) -> str:
    """Majburiy muhit o'zgaruvchisini oladi; yo'q bo'lsa tushunarli xato bilan to'xtaydi."""
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(
            f"❌ .env faylida {name} topilmadi. .env.example dagi namunaga qarang."
        )
    return value


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    model: str
    fallback_models: tuple[str, ...]
    cooldown: float
    allowed_users: frozenset[int]


def load_settings(base_dir: Path) -> Settings:
    """.env ni o'qiydi (avval bot papkasidan, keyin joriy papkadan) va Settings qaytaradi."""
    load_dotenv(base_dir / ".env")
    load_dotenv()  # zaxira: joriy papkadagi .env (mavjud qiymatlarni o'zgartirmaydi)

    fallbacks = tuple(
        m.strip()
        for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite").split(",")
        if m.strip()
    )
    allowed = frozenset(
        int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
    )
    return Settings(
        gemini_api_key=require_env("GEMINI_API_KEY"),
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        fallback_models=fallbacks,
        cooldown=float(os.getenv("COOLDOWN_SECONDS", "2")),
        allowed_users=allowed,
    )
