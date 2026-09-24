# 🧠 Matematika AI Ustozi — Telegram boti

Gemini API asosida ishlaydigan, o'quvchini yo'naltiruvchi (hint tizimi bilan) matematika ustozi.

## Imkoniyatlar

- Sizning **Gem ko'rsatmangiz** (`system_instruction.json`) to'liq qo'llanadi
- Matn va **rasm** (daftardagi masala surati) qabul qiladi
- Har bir foydalanuvchi uchun alohida suhbat xotirasi
- Tugmalar: 💡 Hint · ✅ To'liq yechim · 📝 O'xshash masala · 🔽 Osonroq tushuntir
- `/level` — qiyinlik darajasi (🟢 🔵 🟠 🔴)
- `/reset` — suhbatni tozalash
- Uzun javoblarni bo'lib yuboradi, LaTeX o'rniga oddiy belgilardan foydalanadi
- Spamdan himoya (cooldown) va ixtiyoriy ruxsat ro'yxati

## 1. Kalitlarni olish

1. **Telegram token:** Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → nom va username bering → token oling.
2. **Gemini API kalit:** https://aistudio.google.com/apikey → *Create API key*.

## 2. O'rnatish va ishga tushirish

```bash
cd math-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # so'ng .env ichiga token va kalitni yozing
python bot.py
```

Konsolda `Bot ishga tushdi` chiqsa, Telegram'da botingizga `/start` yuboring.

## 3. Doimiy ishlatish (server)

**Docker bilan:**

```bash
docker build -t math-bot .
docker run -d --restart unless-stopped --env-file .env --name math-bot math-bot
```

**Yoki systemd (VPS):** `/etc/systemd/system/math-bot.service`

```ini
[Unit]
Description=Math Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/math-bot
ExecStart=/opt/math-bot/venv/bin/python bot.py
Restart=always
EnvironmentFile=/opt/math-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now math-bot
```

## Keyingi botlar uchun

Bu kod boshqa botlar uchun ham shablon bo'ladi: yangi botga faqat **yangi token**
va **yangi JSON ko'rsatma** (`SYSTEM_INSTRUCTION_FILE`) kerak.

## Muhim eslatmalar

- `.env` faylini hech kimga bermang va GitHub'ga yuklamang.
- Suhbat tarixi xotirada saqlanadi, bot qayta ishga tushsa tozalanadi. Doimiy saqlash kerak bo'lsa SQLite/Redis qo'shing.
- Gemini API kaliti "location not supported" xatosini bersa, bot ishlayotgan **server** joylashuvi qo'llab-quvvatlanadigan hududda bo'lishi kerak.
- Model nomini `.env` dagi `GEMINI_MODEL` orqali almashtirishingiz mumkin.

---

# 🎓 2-bot: CEFR English Ustozi & Examiner

Fayllar: `cefr_ai_bot.py` va `cefr_system_instruction.json` (bot.py bilan **bir papkada**).

- **Ustoz rejimi:** ingliz tili savollari, grammatika tushuntirish, xatolarni tuzatish, taxminiy CEFR daraja aniqlash.
- **Imtihon rejimi (`/exam`):** real B1 imtihoni: Listening → Reading → Writing → Speaking → yakuniy hisobot.
- Speaking uchun **ovozli xabar** qabul qiladi.

## Ishga tushirish

1. @BotFather'da `/newbot` bilan **yangi, alohida bot** yarating (1-bot tokeni bilan ishlamaydi).
2. `.env` ga `CEFR_BOT_TOKEN=...` qatorini qo'shing.
3. **Ikkinchi terminal** ochib, venv'ni yoqing va:
   ```bash
   python cefr_ai_bot.py
   ```

Ikkala bot bir vaqtda ishlashi uchun ikkita terminal ochiq turishi kerak.
Har bir bot o'z tokeniga ega bo'lishi shart, aks holda `Conflict` xatosi chiqadi.

## Cheklovlar

- Listening real audio bilan emas, matn ko'rinishida o'tkaziladi.
- Suhbat va imtihon holati xotirada saqlanadi: bot qayta ishga tushsa, imtihon boshidan boshlanadi.

---

# 🧩 `botkit` — umumiy kutubxona

Ikkala bot ham bir xil ishni qiladigan kodni (Gemini, xotira, formatlash) `botkit/` papkasidan oladi.
Botning o'zida faqat **prompt, tugmalar va handlerlar** qoladi.

```
math-bot/
├── bot.py                        # 1-bot: Matematika
├── cefr_ai_bot.py                # 2-bot: CEFR English
├── bot_template.py               # yangi bot shabloni
├── system_instruction.json       # 1-bot ko'rsatmasi
├── cefr_system_instruction.json  # 2-bot ko'rsatmasi
├── .env                          # kalitlar (o'zingiz yaratasiz)
├── requirements.txt
└── botkit/
    ├── config.py    # .env va sozlamalar
    ├── prompts.py   # JSON ko'rsatmani promptga aylantirish
    ├── gemini.py    # Gemini + qayta urinish + zaxira model
    ├── engine.py    # xotira, cooldown, ruxsat, xatolarni boshqarish
    └── tg.py        # formatlash, yuborish, Application yaratish
```

## Yangi bot yaratish (3-bot, 4-bot ...)

1. `bot_template.py` ni nusxalab, nomini o'zgartiring (masalan `physics_bot.py`).
2. @BotFather'da yangi bot yarating, tokenni `.env` ga yozing (`NEW_BOT_TOKEN=...`).
3. Yangi JSON ko'rsatma faylini yarating va shablondagi fayl nomini almashtiring.
4. `python physics_bot.py`

Gemini bilan bog'liq xatoliklarni (503, model nomi va h.k.) endi faqat `botkit/` ichida tuzatasiz,
tuzatish barcha botlarga birdan ta'sir qiladi.
