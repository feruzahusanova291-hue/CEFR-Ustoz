"""Telegram bilan ishlash yordamchilari: formatlash, yuborish, ilova yaratish."""

import asyncio
import html
import logging
import re

from telegram import BotCommand, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, ContextTypes

log = logging.getLogger("botkit.tg")


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def to_telegram_html(text: str) -> str:
    """Gemini'ning Markdown javobini Telegram HTML'iga xavfsiz o'giradi."""
    text = html.escape(text, quote=False)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    text = re.sub(r"^\s*\*\s+", "• ", text, flags=re.M)
    return text


def split_text(text: str, limit: int = 3500) -> list[str]:
    """Uzun javobni Telegram limitiga (4096) mos bo'laklarga bo'ladi."""
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks


async def send_reply(message, text: str, markup=None) -> None:
    """Javobni bo'laklab yuboradi; tugmalar oxirgi bo'lakka qo'yiladi."""
    chunks = split_text(text)
    for i, chunk in enumerate(chunks):
        m = markup if i == len(chunks) - 1 else None
        try:
            await message.reply_text(
                to_telegram_html(chunk), parse_mode=ParseMode.HTML, reply_markup=m
            )
        except BadRequest:
            await message.reply_text(chunk, reply_markup=m)  # HTML buzilsa — oddiy matn


async def keep_typing(chat) -> None:
    try:
        while True:
            await chat.send_action(ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


async def download_bytes(file_holder) -> bytes:
    """Photo / Voice kabi obyektdan faylni baytlarga yuklab oladi."""
    tg_file = await file_holder.get_file()
    return bytes(await tg_file.download_as_bytearray())


def build_application(token: str, commands: list[BotCommand]) -> Application:
    """Standart sozlangan Application: parallel xizmat, menyu buyruqlari, xato handleri."""

    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(commands)

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("Handlerda xatolik", exc_info=context.error)

    app = (
        Application.builder()
        .token(token)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )
    app.add_error_handler(on_error)
    return app


def run(app: Application, name: str) -> None:
    log.info("%s ishga tushmoqda...", name)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
