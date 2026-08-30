"""
DiseaseTool — wraps the MobileNetV2 plant disease classifier.

Accepts an optional base64-encoded image from state["disease_image_b64"].
If no image is provided, returns an empty detection result.

Reads: disease_image_b64 (optional), farm_state
Writes: disease_detection
"""
import base64
import io
import time
from typing import Any
from backend.tools.base import BaseTool


class DiseaseTool(BaseTool):
    name = "disease"
    description = (
        "Analyzes a plant leaf image (if provided) using a MobileNetV2 disease classifier "
        "to identify diseases, pests, or health issues. Result is integrated into "
        "the crop advisory for targeted treatment recommendations."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "disease_image_b64": {
                "type": "string",
                "description": "Base64-encoded JPEG/PNG leaf image (optional)",
            },
        },
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        image_b64: str | None = state.get("disease_image_b64")

        if not image_b64:
            return {
                "disease_detection": {
                    "label": "",
                    "confidence": 0.0,
                    "image_provided": False,
                    "suggestions": [],
                }
            }

        t0 = time.perf_counter()
        try:
            from backend.ml.model_cache import ModelCache
            from PIL import Image
            import torch

            cache = ModelCache.get()
            if cache is None or cache.disease_model is None:
                raise RuntimeError("Disease model not loaded")

            # Decode image
            img_bytes = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # Run inference via HuggingFace pipeline (already loaded in cache)
            results = cache.disease_model(image)
            top = results[0] if results else {"label": "Unknown", "score": 0.0}

            label = top.get("label", "Unknown")
            confidence = round(float(top.get("score", 0.0)), 4)

            # Simple suggestion mapping
            suggestions = _get_suggestions(label)

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "disease_detection": {
                    "label": label,
                    "confidence": confidence,
                    "image_provided": True,
                    "suggestions": suggestions,
                    "inference_ms": elapsed_ms,
                },
                "agent_timings": {**state.get("agent_timings", {}), "disease": elapsed_ms},
            }

        except Exception as e:
            return {
                "disease_detection": {
                    "label": "",
                    "confidence": 0.0,
                    "image_provided": True,
                    "error": str(e),
                    "suggestions": [],
                }
            }


def _get_suggestions(label: str) -> list[str]:
    label_lower = label.lower()
    if "healthy" in label_lower:
        return ["Plant appears healthy. Maintain current care routine."]
    if "blight" in label_lower:
        return [
            "Apply copper-based fungicide immediately.",
            "Remove and destroy infected leaves.",
            "Improve air circulation around plants.",
        ]
    if "mite" in label_lower or "spider" in label_lower:
        return [
            "Apply neem oil spray to affected areas.",
            "Increase humidity to deter mites.",
            "Introduce predatory mites as biological control.",
        ]
    if "rust" in label_lower:
        return [
            "Apply sulfur-based fungicide.",
            "Avoid overhead irrigation.",
            "Remove infected plant debris.",
        ]
    if "mosaic" in label_lower or "virus" in label_lower:
        return [
            "Remove and destroy infected plants immediately.",
            "Control aphid and whitefly populations (virus vectors).",
            "Use virus-resistant varieties for replanting.",
        ]
    return [
        f"Disease detected: {label}. Consult local agricultural extension office.",
        "Isolate affected plants to prevent spread.",
    ]
