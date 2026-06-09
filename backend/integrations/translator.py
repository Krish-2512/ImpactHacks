"""
Fast translation via Google Translate's public free endpoint.

No model download, no GPU, no API key required.
Concurrent httpx requests — 80 strings translate in ~2-4 seconds.
Results are persisted to ml_data/translations_cache.json (never re-translated).

Google added Assamese (as), Manipuri/Meitei (mni-Mtei), and Mizo (lus)
in May 2022, so all 7 Agrow languages are supported.
"""
import asyncio
import json
from pathlib import Path

import httpx

CACHE_FILE = Path(__file__).parent.parent.parent / "ml_data" / "translations_cache.json"

# Maps our i18n language codes → Google Translate codes
GOOGLE_CODES: dict[str, str] = {
    "hi":  "hi",        # Hindi
    "as":  "as",        # Assamese
    "bn":  "bn",        # Bengali
    "ne":  "ne",        # Nepali
    "mni": "mni-Mtei",  # Manipuri / Meitei script (added by Google 2022)
    "lus": "lus",       # Mizo / Lushai (added by Google 2022)
}

_cache: dict[str, str] = {}
_cache_loaded = False
_cache_dirty  = False


def _load_cache() -> None:
    global _cache, _cache_loaded
    if _cache_loaded:
        return
    if CACHE_FILE.exists():
        _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    _cache_loaded = True


def _flush_cache() -> None:
    global _cache_dirty
    if not _cache_dirty:
        return
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(_cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _cache_dirty = False


async def _translate_one(
    client: httpx.AsyncClient,
    text: str,
    google_lang: str,
    semaphore: asyncio.Semaphore,
) -> str:
    """Single string → translated string via Google's free endpoint."""
    async with semaphore:
        try:
            r = await client.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "en",
                    "tl": google_lang,
                    "dt": "t",
                    "q": text,
                },
            )
            r.raise_for_status()
            # Response: [[["translated","original",...], ...], null, "en", ...]
            data = r.json()
            return "".join(part[0] for part in data[0] if part[0])
        except Exception:
            return text  # fallback: return original English


async def translate_batch(texts: list[str], target_lang: str) -> list[str]:
    """
    Translate a list of English strings.
    Cached strings are returned instantly; only missing ones hit the network.
    Max 10 concurrent requests to avoid rate-limiting.
    """
    if not texts:
        return texts

    _load_cache()
    google_lang = GOOGLE_CODES[target_lang]

    results: list[str | None] = [None] * len(texts)
    missing: list[int] = []

    for i, text in enumerate(texts):
        key = f"{target_lang}::{text}"
        if key in _cache:
            results[i] = _cache[key]
        else:
            missing.append(i)

    if missing:
        semaphore = asyncio.Semaphore(10)  # max concurrent requests
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            tasks = [
                _translate_one(client, texts[i], google_lang, semaphore)
                for i in missing
            ]
            translated = await asyncio.gather(*tasks)

        global _cache_dirty
        for idx, tr in zip(missing, translated):
            results[idx] = tr
            _cache[f"{target_lang}::{texts[idx]}"] = tr
            _cache_dirty = True

        _flush_cache()

    return [r or t for r, t in zip(results, texts)]
