"""
MultimodalAdvisoryTool — integrates disease image analysis with weather, market,
and RAG advisory in a single cross-modal reasoning pass.

After MobileNetV2 classifies the disease, it constructs a disease-aware RAG query
that incorporates the detected condition, current weather, and sell urgency.
The result enriches crop_advisory with disease-contextualised recommendations.

This tool REPLACES the separate disease + advisory run when an image is provided.
Reads:  disease_image_b64, farm_state, weather_forecast, sell_hold_decisions
Writes: disease_detection, crop_advisory (updated), rag_sources, rag_query,
        advisory_confidence, agent_timings["multimodal"]
"""
import logging
import time
from typing import Any

from backend.tools.base import BaseTool
from backend.tools.disease_tool import DiseaseTool, _get_suggestions

logger = logging.getLogger(__name__)


class MultimodalAdvisoryTool(BaseTool):
    name = "multimodal"
    description = (
        "Combines plant disease image analysis with weather and market context to produce "
        "disease-aware crop recommendations. Use when an image is provided to get "
        "integrated advice instead of running disease and advisory separately."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "disease_image_b64": {
                "type": "string",
                "description": "Base64-encoded leaf/crop image",
            },
        },
        "required": ["disease_image_b64"],
    }

    def __init__(self) -> None:
        self._disease_tool = DiseaseTool()

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()

        # Step 1 — Run disease classification
        disease_result = await self._disease_tool.run(state)
        detection = disease_result.get("disease_detection", {})
        disease_label = detection.get("label", "")
        disease_conf = detection.get("confidence", 0.0)

        # Step 2 — Build disease-aware RAG query
        farm_state = state.get("farm_state", {})
        crops = farm_state.get("primary_crops", [])
        primary_crop = crops[0] if crops else "crop"

        weather = state.get("weather_forecast", {})
        weather_cond = weather.get("Condition", "")
        humidity = weather.get("Humidity", "")

        sell_decisions = state.get("sell_hold_decisions", {})
        sell_urgency_crops = [c for c, d in sell_decisions.items() if "SELL" in str(d).upper()]

        disease_aware_query = _build_rag_query(
            disease_label, primary_crop, weather_cond, humidity, sell_urgency_crops
        )

        # Step 3 — Disease-aware RAG retrieval + advisory generation
        advisory_delta: dict[str, Any] = {}
        try:
            from backend.rag.retriever import retrieve_context_multi_query
            import asyncio

            chunks = await asyncio.to_thread(
                retrieve_context_multi_query,
                disease_aware_query,
                top_k=6,
                score_threshold=0.25,
                compress=True,
            )

            rag_context = "\n\n".join(c.get("text", "") for c in chunks[:4])
            advisory = await _generate_disease_advisory(
                disease_label, disease_conf, rag_context, state
            )

            advisory_delta = {
                "crop_advisory": advisory,
                "rag_query": disease_aware_query,
                "rag_sources": chunks,
                "advisory_confidence": min(0.95, disease_conf + 0.1),
            }
        except Exception as e:
            logger.warning("MultimodalAdvisoryTool RAG step failed: %s", e)
            advisory_delta = {
                "crop_advisory": (
                    f"Disease detected: {disease_label} (confidence: {disease_conf:.0%}). "
                    + " ".join(_get_suggestions(disease_label))
                ),
                "rag_query": disease_aware_query,
                "rag_sources": [],
                "advisory_confidence": disease_conf * 0.8,
            }

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        timings = {**state.get("agent_timings", {}), "multimodal": elapsed_ms}

        return {
            "disease_detection": detection,
            "agent_timings": timings,
            **advisory_delta,
        }


def _build_rag_query(
    disease_label: str,
    crop: str,
    weather_cond: str,
    humidity: str,
    sell_urgency_crops: list[str],
) -> str:
    parts = []
    if disease_label and "healthy" not in disease_label.lower():
        parts.append(f"{disease_label} treatment {crop}")
    else:
        parts.append(f"{crop} cultivation best practices")

    if weather_cond:
        parts.append(f"under {weather_cond} conditions")
    if humidity:
        parts.append(f"humidity {humidity}%")
    if sell_urgency_crops:
        parts.append(f"sell urgency for {', '.join(sell_urgency_crops)}")

    return " ".join(parts)


async def _generate_disease_advisory(
    disease_label: str,
    confidence: float,
    rag_context: str,
    state: dict[str, Any],
) -> str:
    """LLM call to produce integrated disease + context advisory."""
    try:
        from groq import AsyncGroq
        from backend.config import settings

        farm = state.get("farm_state", {})
        crops = ", ".join(farm.get("primary_crops", ["your crops"]))
        location = farm.get("location", "your region")

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        system = (
            "You are an expert agricultural advisor. Given a disease diagnosis and "
            "relevant knowledge base excerpts, provide specific, actionable treatment "
            "and management advice. Be concise (3-5 bullet points)."
        )
        prompt = (
            f"Farmer location: {location}\nCrops: {crops}\n\n"
            f"Disease diagnosed: {disease_label} (confidence: {confidence:.0%})\n\n"
            f"Relevant knowledge:\n{rag_context[:800]}\n\n"
            "Provide integrated disease management recommendations considering the farm context."
        )

        resp = await client.chat.completions.create(
            model=settings.GROQ_MODEL_FAST,
            temperature=0.3,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        logger.warning("Multimodal advisory LLM call failed: %s", e)
        return (
            f"Disease detected: {disease_label} (confidence: {confidence:.0%}). "
            + " ".join(_get_suggestions(disease_label))
        )
