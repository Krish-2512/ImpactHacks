"""
Plant disease detector using MobileNetV2 fine-tuned on PlantVillage (38 classes).

The HuggingFace pipeline API for this model breaks on transformers ≥ 4.47 because
the model repo lacks an `image_processor_type` key. We load model weights directly
and apply standard MobileNetV2 ImageNet preprocessing via torchvision instead.
"""
from PIL import Image
import io
from backend.config import settings

TREATMENT_MAP = {
    # ── Apple ────────────────────────────────────────────────────────────────
    "Apple___Apple_scab": "Apply fungicide (captan or mancozeb) during wet spring. Remove and destroy fallen leaves.",
    "Apple___Black_rot": "Prune infected branches 8 inches below lesions. Apply copper fungicide after pruning.",
    "Apple___Cedar_apple_rust": "Apply myclobutanil fungicide at pink bud stage. Remove nearby juniper trees if possible.",
    "Apple___healthy": "Plant appears healthy. Continue regular monitoring.",
    # ── Blueberry / Cherry / Raspberry / Strawberry ───────────────────────
    "Blueberry___healthy": "Plant appears healthy.",
    "Cherry_(including_sour)___Powdery_mildew": "Apply sulfur or potassium bicarbonate spray. Prune for better air circulation.",
    "Cherry_(including_sour)___healthy": "Plant appears healthy.",
    "Raspberry___healthy": "Plant appears healthy.",
    "Strawberry___Leaf_scorch": "Remove infected leaves immediately. Apply captan fungicide. Avoid wetting foliage.",
    "Strawberry___healthy": "Plant appears healthy.",
    # ── Corn / Soybean / Squash ───────────────────────────────────────────
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Apply strobilurin fungicide. Practice crop rotation with non-host crops.",
    "Corn_(maize)___Common_rust_": "Apply propiconazole fungicide at early infection. Plant resistant varieties next season.",
    "Corn_(maize)___Northern_Leaf_Blight": "Apply azoxystrobin at early tasseling. Use resistant hybrids.",
    "Corn_(maize)___healthy": "Plant appears healthy.",
    "Soybean___healthy": "Plant appears healthy.",
    "Squash___Powdery_mildew": "Apply neem oil or sulfur spray weekly. Water at base, avoid overhead irrigation.",
    # ── Grape ─────────────────────────────────────────────────────────────
    "Grape___Black_rot": "Remove mummified fruit. Apply mancozeb fungicide before and during wet weather.",
    "Grape___Esca_(Black_Measles)": "Prune infected wood during dry weather. Remove severely affected vines.",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Apply copper-based fungicide. Improve canopy ventilation by leaf removal.",
    "Grape___healthy": "Plant appears healthy.",
    # ── Orange / Citrus ───────────────────────────────────────────────────
    "Orange___Haunglongbing_(Citrus_greening)": "URGENT: Remove and destroy infected trees. Control Asian citrus psyllid with imidacloprid.",
    # ── Peach / Pepper ───────────────────────────────────────────────────
    "Peach___Bacterial_spot": "Apply copper hydroxide spray every 10–14 days. Avoid overhead irrigation.",
    "Peach___healthy": "Plant appears healthy.",
    "Pepper,_bell___Bacterial_spot": "Apply copper-based bactericide. Rotate crops for 2+ years. Avoid working in wet fields.",
    "Pepper,_bell___healthy": "Plant appears healthy.",
    # ── Potato ───────────────────────────────────────────────────────────
    "Potato___Early_blight": "Apply chlorothalonil or mancozeb every 7 days. Ensure proper spacing for air circulation.",
    "Potato___Late_blight": "URGENT: Apply metalaxyl or dimethomorph immediately. Destroy infected plants — do not compost.",
    "Potato___healthy": "Plant appears healthy.",
    # ── Tomato ───────────────────────────────────────────────────────────
    "Tomato___Bacterial_spot": "Apply copper-based bactericide. Remove infected leaves. Avoid overhead watering.",
    "Tomato___Early_blight": "Apply mancozeb or chlorothalonil every 7–10 days. Mulch around base to prevent soil splash.",
    "Tomato___Late_blight": "URGENT: Apply metalaxyl or cymoxanil immediately. Remove and burn infected tissue.",
    "Tomato___Leaf_Mold": "Improve ventilation. Reduce humidity below 85%. Apply chlorothalonil fungicide.",
    "Tomato___Septoria_leaf_spot": "Remove lower infected leaves. Apply mancozeb. Avoid wetting foliage.",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Apply neem oil or abamectin. Spray undersides of leaves thoroughly. Increase ambient humidity.",
    "Tomato___Target_Spot": "Apply azoxystrobin or pyraclostrobin fungicide. Improve air circulation.",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "URGENT: Remove infected plants immediately. Control whitefly with imidacloprid or yellow sticky traps.",
    "Tomato___Tomato_mosaic_virus": "Remove infected plants. Disinfect tools with 10% bleach. Plant certified disease-free seeds.",
    "Tomato___healthy": "Plant appears healthy. Continue regular monitoring.",
}

# Disease-type keyword → generic treatment guidance
_DISEASE_KEYWORD_ADVICE = {
    "late_blight":       ("URGENT: Apply metalaxyl or cymoxanil fungicide immediately. Remove and destroy infected tissue. Do not compost.", "urgent"),
    "early_blight":      ("Apply mancozeb or chlorothalonil every 7–10 days. Remove lower infected leaves. Mulch around base.", "moderate"),
    "blight":            ("Apply copper-based or mancozeb fungicide. Remove infected plant parts immediately. Improve air circulation.", "moderate"),
    "powdery_mildew":    ("Apply sulfur-based or potassium bicarbonate spray. Improve air circulation. Avoid overhead watering.", "moderate"),
    "downy_mildew":      ("Apply fosetyl-aluminium or mancozeb. Remove infected leaves. Reduce leaf wetness duration.", "moderate"),
    "rust":              ("Apply propiconazole or tebuconazole fungicide. Remove and destroy infected leaves. Avoid excessive nitrogen.", "moderate"),
    "leaf_spot":         ("Apply chlorothalonil or mancozeb every 10–14 days. Remove infected leaves. Avoid wetting foliage.", "moderate"),
    "bacterial_spot":    ("Apply copper-based bactericide. Avoid overhead irrigation. Rotate crops for 2 years.", "moderate"),
    "bacterial_wilt":    ("Remove and destroy wilted plants. Disinfect tools. Control cucumber beetle vectors. Practice 3-year crop rotation.", "urgent"),
    "mosaic_virus":      ("Remove and destroy infected plants. Control aphid vectors with neem oil or imidacloprid. Disinfect all tools.", "urgent"),
    "yellow_curl_virus": ("Remove infected plants. Control whitefly with imidacloprid or yellow sticky traps.", "urgent"),
    "black_rot":         ("Apply copper fungicide. Remove infected plant material. Improve drainage and air circulation.", "moderate"),
    "leaf_mold":         ("Improve ventilation and reduce humidity. Apply chlorothalonil or copper fungicide.", "moderate"),
    "anthracnose":       ("Apply mancozeb or carbendazim fungicide. Avoid overhead irrigation. Remove infected fruit and leaves.", "moderate"),
    "cercospora":        ("Apply strobilurin or mancozeb fungicide. Practice crop rotation. Remove crop debris after harvest.", "moderate"),
    "scab":              ("Apply captan or myclobutanil fungicide at early symptom stage. Remove fallen infected leaves.", "moderate"),
    "canker":            ("Prune and destroy infected branches. Apply copper paste on cut surfaces. Avoid wounds during wet weather.", "moderate"),
    "wilt":              ("Remove infected plants. Improve soil drainage. Solarise soil between seasons. Avoid water-logging.", "moderate"),
    "spider_mite":       ("Apply neem oil or abamectin. Spray leaf undersides. Increase humidity. Remove heavily infested leaves.", "moderate"),
    "aphid":             ("Apply neem oil or imidacloprid spray. Use yellow sticky traps. Encourage natural predators.", "moderate"),
    "shoot_borer":       ("Apply chlorpyrifos or spinosad. Remove and destroy infested shoots weekly. Use pheromone traps.", "urgent"),
    "fruit_borer":       ("Apply spinosad or emamectin benzoate. Install pheromone traps. Remove infested fruit immediately.", "urgent"),
    "greening":          ("URGENT: Remove and destroy infected trees. Control psyllid vector with imidacloprid. Plant certified disease-free nursery stock.", "urgent"),
}


def _smart_fallback(label: str, crop: str, disease: str) -> tuple[str, str]:
    """Return (treatment_text, severity) for labels not in TREATMENT_MAP."""
    label_lower = label.lower().replace(" ", "_")
    disease_lower = disease.lower().replace(" ", "_")

    for keyword, (advice, severity) in _DISEASE_KEYWORD_ADVICE.items():
        if keyword in label_lower or keyword in disease_lower:
            return (
                f"{advice} (Detected: {disease} on {crop}. "
                f"For region-specific guidance contact your local KVK.)",
                severity,
            )

    # Last resort — at least name the disease
    return (
        f"Disease identified: {disease} on {crop}. "
        "Apply broad-spectrum fungicide/bactericide as a precaution. "
        "Isolate affected plants and consult your local Krishi Vigyan Kendra (KVK) "
        "or call the Kisan Call Centre: 1800-180-1551 (toll-free).",
        "moderate",
    )

_model = None
_labels = None


def _preprocess(image: Image.Image):
    """MobileNetV2 ImageNet preprocessing using only PIL + numpy (no torchvision needed)."""
    import numpy as np
    import torch

    # 1. Resize so shorter side = 256
    w, h = image.size
    if w <= h:
        new_w, new_h = 256, int(h * 256 / w)
    else:
        new_w, new_h = int(w * 256 / h), 256
    image = image.resize((new_w, new_h), Image.BILINEAR)

    # 2. Center crop to 224×224
    w, h = image.size
    left = (w - 224) // 2
    top  = (h - 224) // 2
    image = image.crop((left, top, left + 224, top + 224))

    # 3. To float32 tensor in [0, 1]
    arr = np.array(image, dtype=np.float32) / 255.0  # H×W×3

    # 4. Normalize with ImageNet mean/std
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr  = (arr - mean) / std

    # 5. HWC → CHW → [1, 3, 224, 224]
    return torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0)


def _load_model():
    global _model, _labels  # must declare global to modify module-level vars
    if _model is not None:
        return

    import torch
    from transformers import AutoModelForImageClassification, AutoConfig

    model_id = settings.DISEASE_MODEL_ID

    config = AutoConfig.from_pretrained(model_id)
    _labels = config.id2label  # {0: "Apple___Apple_scab", ...}

    _model = AutoModelForImageClassification.from_pretrained(model_id)
    _model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    _model.eval()

    print(f"Disease model loaded: {model_id} ({len(_labels)} classes)")


def predict(image_bytes: bytes) -> dict:
    import torch
    import torch.nn.functional as F

    _load_model()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = _preprocess(image)  # [1, 3, 224, 224]

    device = next(_model.parameters()).device
    tensor = tensor.to(device)

    with torch.no_grad():
        output = _model(tensor)
        # Handle both object-with-logits and raw tuple/tensor outputs
        if hasattr(output, "logits"):
            logits = output.logits
        elif isinstance(output, (tuple, list)):
            logits = output[0]
        else:
            logits = output
        probs = F.softmax(logits.float(), dim=-1)[0]

    n_classes = probs.shape[0]
    top_k = min(3, n_classes)
    top_vals, top_idxs = torch.topk(probs, k=top_k)
    results = [
        {"label": _labels[idx.item()], "confidence": round(score.item() * 100, 1)}
        for idx, score in zip(top_idxs, top_vals)
    ]

    top = results[0]
    label: str = top["label"]
    confidence: float = top["confidence"]

    parts = label.split("___")
    crop    = parts[0].replace("_", " ") if parts else "Unknown"
    disease = parts[1].replace("_", " ") if len(parts) > 1 else label
    is_healthy = "healthy" in label.lower()

    if is_healthy:
        treatment = f"{crop} plant appears healthy. Continue regular monitoring and care."
        severity  = "none"
    elif label in TREATMENT_MAP:
        treatment = TREATMENT_MAP[label]
        severity  = "urgent" if "URGENT" in treatment else "moderate"
    else:
        treatment, severity = _smart_fallback(label, crop, disease)

    return {
        "label":       label,
        "crop":        crop,
        "disease":     disease,
        "is_healthy":  is_healthy,
        "confidence":  confidence,
        "treatment":   treatment,
        "severity":    severity,
        "all_predictions": results,
    }
