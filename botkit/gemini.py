"""Gemini REST API bilan ishlash (tashqi Gemini kutubxonasiz).

Faqat Python'ning standart kutubxonasi ishlatiladi, shuning uchun 32-bit Windows'da
ham hech qanday kompilyatsiya talab qilinmaydi. Band bo'lsa qayta urinadi,
model topilmasa zaxira modelga o'tadi.
"""

import asyncio
import base64
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

log = logging.getLogger("botkit.gemini")

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
RETRYABLE_CODES = (429, 500, 502, 503, 504)
REQUEST_TIMEOUT = 120  # soniya (fikrlaydigan modellar sekin javob berishi mumkin)


class APIError(Exception):
    """Gemini xatosi. code=None bo'lsa — tarmoq xatosi (internet yo'q, timeout va h.k.)."""

    def __init__(self, code: int | None, message: str = ""):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class Content:
    """Suhbatdagi bitta xabar: role = 'user' yoki 'model'."""

    role: str
    parts: list


def text_part(text: str) -> dict:
    return {"text": text}


def media_part(data: bytes, mime_type: str) -> dict:
    """Rasm (image/jpeg), ovoz (audio/ogg) va h.k. uchun."""
    return {
        "inlineData": {
            "mimeType": mime_type,
            "data": base64.b64encode(data).decode("ascii"),
        }
    }


def is_overloaded(exc: Exception) -> bool:
    """Gemini band yoki limit tugagan (503/429...) holatmi?"""
    return isinstance(exc, APIError) and exc.code in RETRYABLE_CODES


def _post(url: str, api_key: str, payload: dict, timeout: float) -> dict:
    """Bloklovchi HTTP so'rov (asyncio.to_thread orqali chaqiriladi)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:  # URLError'dan oldin turishi shart
        body = e.read().decode("utf-8", "replace")
        message = body[:300]
        try:
            message = json.loads(body)["error"]["message"]
        except Exception:
            pass
        raise APIError(e.code, message) from None
    except (urllib.error.URLError, OSError) as e:  # DNS, ulanish, timeout
        raise APIError(None, f"tarmoq xatosi: {e}") from None


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        log.warning("Javob bo'sh (promptFeedback=%s)", data.get("promptFeedback"))
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()


class GeminiService:
    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_models=(),
        *,
        base_url: str = API_BASE,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.models = [model] + [m for m in fallback_models if m != model]

    async def generate(
        self, contents, system_instruction: str, max_output_tokens: int = 8192
    ) -> str:
        """Javob matnini qaytaradi. Band bo'lsa qayta urinadi, so'ng zaxira modelga o'tadi."""
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": c.role, "parts": c.parts} for c in contents],
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }
        last_exc: Exception | None = None
        for model in self.models:
            url = f"{self.base_url}/{model}:generateContent"
            for attempt in range(3):
                try:
                    data = await asyncio.to_thread(
                        _post, url, self.api_key, payload, self.timeout
                    )
                    return _extract_text(data)
                except APIError as e:
                    last_exc = e
                    if e.code is None:  # tarmoq xatosi: zaxira model yordam bermaydi
                        log.warning("%s: %s (urinish %d/2)", model, e.message, attempt + 1)
                        if attempt < 1:
                            await asyncio.sleep(1)
                            continue
                        raise
                    if e.code in RETRYABLE_CODES:
                        log.warning("%s: xato %s (urinish %d/3)", model, e.code, attempt + 1)
                        if attempt < 2:
                            await asyncio.sleep(2**attempt)  # 1s, 2s
                        continue
                    if e.code == 404:  # model topilmadi -> keyingisiga o'tamiz
                        log.warning("%s topilmadi, keyingi modelga o'tilmoqda", model)
                        break
                    raise
        if last_exc is None:
            raise RuntimeError("Hech qanday model sozlanmagan")
        raise last_exc
