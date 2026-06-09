"""
Translation endpoint — public (no auth required).
Translates English UI strings to any supported language via Google Translate.
Results are cached server-side in ml_data/translations_cache.json.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.integrations.translator import translate_batch, GOOGLE_CODES

router = APIRouter(prefix="/translate", tags=["Translation"])

SUPPORTED = list(GOOGLE_CODES.keys())


class TranslateRequest(BaseModel):
    texts:       list[str] = Field(..., max_length=300)
    target_lang: str       = Field(..., description="hi | as | bn | ne | mni | lus")


@router.post("/")
async def translate(body: TranslateRequest):
    if body.target_lang == "en":
        return {"translations": body.texts, "lang": "en", "from_cache": True}

    if body.target_lang not in SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{body.target_lang}'. Supported: {SUPPORTED}",
        )

    if not body.texts:
        return {"translations": [], "lang": body.target_lang}

    try:
        results = await translate_batch(body.texts, body.target_lang)
        return {"translations": results, "lang": body.target_lang}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation error: {exc}")


@router.get("/supported")
async def supported_languages():
    return {
        "provider":  "Google Translate (free public endpoint)",
        "model":     "none — web API, no download required",
        "source":    "English",
        "targets":   GOOGLE_CODES,
    }
