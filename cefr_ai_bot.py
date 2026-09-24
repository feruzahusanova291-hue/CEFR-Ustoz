"""
🎓 2-bot: CEFR English Ustozi & Examiner (Telegram + Gemini)

Ikki rejim:
  • USTOZ  (standart) — ingliz tili savollari, grammatika, xatolarni tuzatish,
                        CEFR darajasini taxminiy aniqlash.
  • IMTIHON (/exam)   — cefr_system_instruction.json asosidagi qat'iy B1 imtihoni
                        (Listening → Reading → Writing → Speaking → Final report).

Ishga tushirish:  python cefr_ai_bot.py
DIQQAT: bu bot uchun @BotFather'dan ALOHIDA bot (yangi token) kerak: CEFR_BOT_TOKEN.
Umumiy kod `botkit/` kutubxonasida.
"""

import os
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from botkit import (
    TELEGRAM_FORMAT_RULES,
    ChatEngine,
    GeminiService,
    build_application,
    download_bytes,
    load_json_instruction,
    load_settings,
    media_part,
    require_env,
    run,
    setup_logging,
    text_part,
)

BASE_DIR = Path(__file__).resolve().parent
setup_logging()
settings = load_settings(BASE_DIR)
TOKEN = require_env("CEFR_BOT_TOKEN")
EXAM_FILE = BASE_DIR / os.getenv("CEFR_SYSTEM_INSTRUCTION_FILE", "cefr_system_instruction.json")
TUTOR_MAX_HISTORY = int(os.getenv("CEFR_TUTOR_HISTORY", "20"))
EXAM_MAX_HISTORY = int(os.getenv("CEFR_EXAM_HISTORY", "300"))  # imtihon tarixi kesilmasin
MAX_VOICE_BYTES = 10 * 1024 * 1024
MAX_OUTPUT_TOKENS = 16384

engine = ChatEngine(
    settings, GeminiService(settings.gemini_api_key, settings.model, settings.fallback_models)
)

# --------------------------------------------------------------------------- #
# System promptlar
# --------------------------------------------------------------------------- #
TUTOR_PROMPT = (
    """Sen — CEFR (A1–C2) asosida ishlaydigan professional ingliz tili ustozisan.
10+ yillik tajribaga ega o'qituvchi va CEFR/IELTS tayyorlov murabbiyisan.
Ohang: sabrli, aniq, rag'batlantiruvchi. O'quvchini hech qachon kamsitmaysan.

VAZIFALARING
1. Ingliz tili bo'yicha savollarga javob berish: grammatika, lug'at, so'z tanlash,
   o'xshash so'zlar farqi, talaffuz, yozish, tarjima.
2. Grammatikani tushuntirish. Har bir mavzuda quyidagi tartibga amal qil:
   (a) qoida va formula, (b) qachon ishlatiladi, (c) 3 ta inglizcha misol va
   tarjimasi, (d) tipik xatolar, (e) 2–3 ta qisqa mini-mashq.
   Mini-mashq javoblarini darhol ochma; o'quvchi javob berganda tekshir.
3. O'quvchining inglizcha yozgan matnidagi xatolarni tuzat:
   Xato → To'g'ri variant → Sabab.
4. CEFR darajasini aniqlashga yordam ber. O'quvchi so'rasa, avval 5–6 ta qisqa
   diagnostik savol ber (A1 dan B2 gacha oshib boruvchi: grammatika, lug'at va
   2–3 gapdan iborat yozma javob). Javoblar kelgach, taxminiy darajani (masalan,
   A2, B1-, B1, B1+, B2) va sabablarini ayt. Bu faqat TAXMINIY natija ekanini,
   to'liq va aniq natija uchun /exam buyrug'i (real imtihon rejimi) borligini eslat.

QOIDALAR
- Tushuntirishni o'quvchi yozgan tilda (o'zbek yoki rus) ber, misollar esa inglizcha bo'lsin.
  O'quvchi inglizcha yozsa, sodda inglizcha va zarur joyda o'zbekcha izoh ber.
- Tushuntirish darajasini o'quvchiga moslashtir: A1–A2 uchun oddiy so'zlar va
  qisqa gaplar, B1+ uchun batafsilroq.
- Aniq bo'l. Ishonchsiz bo'lsang, buni ochiq ayt va taxmin qilma.
- Ingliz tiliga aloqasi yo'q so'rovlarga muloyimlik bilan «men ingliz tili ustoziman»
  deb, mavzuga qaytishni taklif qil.
- Ovozli xabar kelsa: aytilganini yozib ber (transkripsiya), so'ng grammatika,
  lug'at va ravonlik bo'yicha fikr bildir. Talaffuz haqidagi fikring taxminiy
  ekanini ayt.
"""
    + TELEGRAM_FORMAT_RULES
)

EXAM_EXTRA_RULES = """
=== TELEGRAM UCHUN IMTIHON QOIDALARI (yuqoridagi JSON'ga qo'shimcha) ===
- Bu matnli Telegram chat. Har bir xabarda FAQAT bitta topshiriq/savol ber
  (Reading matni va Writing topshirig'i bundan mustasno: matn bitta xabarda beriladi,
  savollar alohida xabarlarda birma-bir).
- Imtihon davomida to'g'ri/noto'g'ri, hint, tarjima, grammatik tuzatish BERMA.
  O'quvchi yordam so'rasa, qisqa va muloyim: «Imtihon paytida yordam berilmaydi.
  Iltimos, o'z bilimingiz asosida javob bering.» de. Imtihondan chiqish uchun
  /stop buyrug'i borligini ayt.
- LISTENING: Real audio yo'q. Shuning uchun listening passage'ni bitta xabarda matn
  ko'rinishida ber va «Passage'ni bir marta diqqat bilan o'qing» deb ayt. Savollarni
  alohida xabarlarda ketma-ket ber. Passage matnini savollardan keyin QAYTA
  takrorlama, javoblarni va transcriptni section tugamaguncha ko'rsatma.
  Final reportda Listening matn asosida o'tkazilgani va real audio bo'lmagani
  cheklov sifatida yozilsin.
- SPEAKING: O'quvchi ovozli xabar (voice message) yuborishi mumkin. Speaking qismida
  ovozli javob so'ra. Ovoz kelsa, uni diqqat bilan tingla va Pronunciation hamda
  Fluency'ni ham baholay olasan. Faqat matn kelsa, pronunciation va real-time fluency
  to'liq baholanmasligini final reportda aniq ko'rsat.
- Har bir section oxirida natijani ko'rsatma; faqat section tugaganini ayt va
  keyingisiga tayyorligini so'ra (JSON'dagi qoidalarga muvofiq). To'liq natija va
  feedback faqat FINAL REPORT'da beriladi.
- Final report'ni jadval o'rniga aniq matnli bo'limlar va emoji belgilar bilan
  chiroyli yoz (Telegram jadvalni ko'rsatmaydi).
- Agar xabar «[SYSTEM EVENT]» bilan boshlansa, bu o'quvchi emas, dastur yuborgan
  ichki signal; unga START_PROTOCOL bo'yicha javob ber.
"""

EXAM_PROMPT = load_json_instruction(
    EXAM_FILE,
    preamble=(
        "Quyidagi JSON — sening imtihon o'tkazish qoidalaringni belgilaydi. "
        "Unga qat'iy amal qil:"
    ),
    suffix=EXAM_EXTRA_RULES + TELEGRAM_FORMAT_RULES,
)

# --------------------------------------------------------------------------- #
# Rejim holati
# --------------------------------------------------------------------------- #
user_mode: dict[int, str] = {}  # "tutor" | "exam"


def get_mode(user_id: int) -> str:
    return user_mode.get(user_id, "tutor")


# Tugmalar faqat ustoz rejimida ko'rinadi — imtihonda hint bo'lmaydi
TUTOR_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📝 Mashq bering", callback_data="practice"),
            InlineKeyboardButton("🔎 Darajamni aniqla", callback_data="level"),
        ],
        [
            InlineKeyboardButton("🔁 Soddaroq tushuntir", callback_data="simpler"),
            InlineKeyboardButton("🎓 CEFR imtihon", callback_data="exam"),
        ],
    ]
)

CALLBACK_PROMPTS = {
    "practice": "Shu mavzu bo'yicha 5 ta qisqa mashq ber. Javoblarni hozir aytma, "
    "men yechib bo'lgach tekshirasan.",
    "level": "CEFR darajamni taxminiy aniqlashda yordam ber. Avval 5–6 ta qisqa "
    "diagnostik savol ber (A1 dan B2 gacha oshib boruvchi) va javoblarimni kut.",
    "simpler": "Buni tushunmadim. Soddaroq so'zlar va ko'proq misollar bilan qayta tushuntir.",
}


async def ask(message, user_id: int, parts: list) -> None:
    mode = get_mode(user_id)
    exam = mode == "exam"
    await engine.process(
        message,
        user_id,
        parts,
        system_instruction=EXAM_PROMPT if exam else TUTOR_PROMPT,
        max_history=EXAM_MAX_HISTORY if exam else TUTOR_MAX_HISTORY,
        session_key=(user_id, mode),  # ustoz va imtihon tarixlari alohida
        markup=None if exam else TUTOR_KEYBOARD,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


async def begin_exam(message, user_id: int) -> None:
    user_mode[user_id] = "exam"
    engine.clear((user_id, "exam"))
    await ask(
        message,
        user_id,
        [
            text_part(
                "[SYSTEM EVENT] The student has just opened the examination. "
                "Follow START_PROTOCOL: send the welcome message and the instructions, "
                "and ask the student to type 'START EXAM'."
            )
        ],
    )


# --------------------------------------------------------------------------- #
# Handlerlar
# --------------------------------------------------------------------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "do'stim"
    user_mode[update.effective_user.id] = "tutor"
    await update.message.reply_text(
        f"👋 Salom, {name}! Men — CEFR English ustozingman 🎓\n\n"
        "Ikki xil ishlayman:\n\n"
        "📚 USTOZ (hozirgi rejim)\n"
        "Ingliz tili haqida istalgan savol bering, grammatikani tushuntiraman, "
        "yozganlaringizdagi xatolarni tuzataman va darajangizni taxminan aniqlashga yordam beraman.\n\n"
        "🎓 IMTIHON (/exam)\n"
        "Real CEFR B1 imtihoniga yaqin format: Listening, Reading, Writing, Speaking va yakuniy hisobot. "
        "Imtihon paytida yordam va hint berilmaydi.\n\n"
        "Buyruqlar:\n"
        "/exam — imtihonni boshlash\n"
        "/stop — imtihondan chiqish\n"
        "/reset — suhbatni tozalash\n"
        "/help — yordam\n\n"
        "Boshlash uchun savol yozing, masalan: «Present Perfect nima?» 🙂"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 Ustoz rejimi:\n"
        "• Grammatika, lug'at, so'zlar farqi haqida so'rang\n"
        "• Inglizcha matn yozing — xatolarini tuzataman\n"
        "• «Darajamni aniqla» tugmasini bosing\n"
        "• Ovozli xabar yuborsangiz, tinglab fikr bildiraman\n\n"
        "🎓 Imtihon rejimi (/exam):\n"
        "• 4 ta section: Listening → Reading → Writing → Speaking\n"
        "• Yordam, tarjima va hint yo'q, natija oxirida beriladi\n"
        "• Speaking qismida ovozli xabar yuboring (talaffuz ham baholanadi)\n"
        "• Imtihonni tugatmasdan chiqsangiz (/stop), yakuniy hisobot berilmaydi\n\n"
        "Cheklov: Listening matn ko'rinishida o'tkaziladi (real audio yo'q)."
    )


async def exam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await begin_exam(update.message, update.effective_user.id)


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if get_mode(uid) != "exam":
        await update.message.reply_text("ℹ️ Siz hozir imtihonda emassiz. Boshlash uchun /exam.")
        return
    user_mode[uid] = "tutor"
    engine.clear((uid, "exam"))
    await update.message.reply_text(
        "🛑 Imtihon to'xtatildi. Yakuniy hisobot berilmadi.\n"
        "Ustoz rejimiga qaytdingiz. Yangi imtihon uchun /exam."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if get_mode(uid) == "exam":
        await update.message.reply_text(
            "ℹ️ Imtihon davomida /reset ishlamaydi. Chiqish uchun /stop, qayta boshlash uchun /exam."
        )
        return
    engine.clear((uid, "tutor"))
    await update.message.reply_text("🔄 Suhbat tozalandi. Yangi savolingizni yozing!")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = query.from_user.id

    if get_mode(uid) == "exam" and query.data != "exam":
        await query.answer("Imtihon davomida bu tugma ishlamaydi.", show_alert=True)
        return
    await query.answer()

    try:  # eski xabardagi tugmalarni olib tashlaymiz
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass

    if query.data == "exam":
        await begin_exam(query.message, uid)
        return

    prompt = CALLBACK_PROMPTS.get(query.data)
    if prompt:
        await ask(query.message, uid, [text_part(prompt)])


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ask(update.message, update.effective_user.id, [text_part(update.message.text)])


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await download_bytes(update.message.photo[-1])
    caption = (
        update.message.caption
        or "Rasmdagi ingliz tili topshirig'i yoki matnini o'qib, tahlil qil."
    )
    await ask(
        update.message,
        update.effective_user.id,
        [media_part(data, "image/jpeg"), text_part(caption)],
    )


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice
    if voice.file_size and voice.file_size > MAX_VOICE_BYTES:
        await update.message.reply_text("🎙 Ovozli xabar juda katta. Qisqaroq yuboring.")
        return
    data = await download_bytes(voice)

    uid = update.effective_user.id
    if get_mode(uid) == "exam":
        note = "[The student answered with a voice message (spoken response).]"
    else:
        note = (
            "Ovozli xabarimni tinglab: 1) aytganimni yozib ber, 2) grammatika, lug'at va "
            "ravonlik bo'yicha fikr bildir (talaffuz haqidagi fikring taxminiy bo'lsin)."
        )
    await ask(update.message, uid, [media_part(data, "audio/ogg"), text_part(note)])


async def on_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📎 Hozircha matn, rasm va ovozli xabar qabul qila olaman.")


def main() -> None:
    app = build_application(
        TOKEN,
        [
            BotCommand("start", "Botni boshlash"),
            BotCommand("exam", "CEFR imtihonini boshlash"),
            BotCommand("stop", "Imtihondan chiqish"),
            BotCommand("reset", "Suhbatni tozalash"),
            BotCommand("help", "Yordam"),
        ],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("exam", exam_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(practice|level|simpler|exam)$"))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.VOICE, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(
        MessageHandler(~filters.COMMAND & ~filters.TEXT & ~filters.PHOTO & ~filters.VOICE, on_other)
    )
    run(app, f"CEFR boti (model: {settings.model})")


if __name__ == "__main__":
    main()
