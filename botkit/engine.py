"""ChatEngine: har bir xabarni qayta ishlash (ruxsat, cooldown, xotira, Gemini, javob)."""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Hashable

from .config import Settings
from .gemini import APIError, Content, GeminiService, is_overloaded, text_part
from .tg import keep_typing, send_reply

log = logging.getLogger("botkit.engine")

EMPTY_REPLY = "🤔 Javob shakllantira olmadim. Iltimos, qayta yuborib ko'ring."


def trim_history(history: list, limit: int) -> None:
    """Tarixni oxirgi `limit` ta xabarga qisqartiradi; doim 'user' bilan boshlanadi."""
    del history[:-limit]
    while history and history[0].role != "user":
        history.pop(0)


class ChatEngine:
    def __init__(self, settings: Settings, gemini: GeminiService):
        self.settings = settings
        self.gemini = gemini
        self.histories: dict[Hashable, list] = defaultdict(list)
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.last_call: dict[int, float] = {}

    def clear(self, session_key: Hashable) -> None:
        self.histories.pop(session_key, None)

    def is_allowed(self, user_id: int) -> bool:
        allowed = self.settings.allowed_users
        return not allowed or user_id in allowed

    async def _ask(self, key, parts, system_instruction, max_history, max_output_tokens) -> str:
        history = self.histories[key]
        history.append(Content("user", parts))
        trim_history(history, max_history)
        try:
            text = await self.gemini.generate(history, system_instruction, max_output_tokens)
        except Exception:
            history.pop()  # muvaffaqiyatsiz so'rovni tarixdan olib tashlaymiz
            raise
        if not text:
            history.pop()
            return EMPTY_REPLY
        history.append(Content("model", [text_part(text)]))
        trim_history(history, max_history)
        return text

    async def process(
        self,
        message,
        user_id: int,
        parts: list,
        *,
        system_instruction: str,
        max_history: int,
        session_key: Hashable | None = None,
        markup=None,
        max_output_tokens: int = 8192,
    ) -> None:
        """Foydalanuvchi xabarini Gemini'ga yuboradi va javobni Telegramga qaytaradi."""
        if not self.is_allowed(user_id):
            await message.reply_text(
                "⛔ Kechirasiz, sizga bu botdan foydalanishga ruxsat berilmagan."
            )
            return

        now = time.monotonic()
        if now - self.last_call.get(user_id, 0) < self.settings.cooldown:
            await message.reply_text("⏳ Iltimos, bir necha soniya kuting.")
            return
        self.last_call[user_id] = now

        key = user_id if session_key is None else session_key
        async with self.locks[user_id]:
            typing_task = asyncio.create_task(keep_typing(message.chat))
            try:
                answer = await self._ask(
                    key, parts, system_instruction, max_history, max_output_tokens
                )
                await send_reply(message, answer, markup)
            except APIError as e:
                log.error("Gemini API xatosi: %s", e)
                if is_overloaded(e):
                    await message.reply_text(
                        "⏳ Gemini serveri hozir juda band. Bir daqiqadan so'ng qayta yozing."
                    )
                else:
                    await message.reply_text("⚠️ Gemini bilan bog'lanishda xatolik yuz berdi.")
            except Exception:
                log.exception("So'rovda xatolik")
                await message.reply_text(
                    "⚠️ Kutilmagan xatolik yuz berdi. Bir ozdan so'ng qayta urinib ko'ring."
                )
            finally:
                typing_task.cancel()
