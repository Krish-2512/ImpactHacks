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
    "Apple___Apple_scab": "Apply fungicide (captan or mancozeb) during wet spring. Remove fallen leaves.",
    "Apple___Black_rot": "Prune infected branches 8 inches below lesions. Apply copper fungicide.",
    "Apple___Cedar_apple_rust": "Apply myclobutanil fungicide. Remove nearby juniper trees if possible.",
    "Apple___healthy": "Plant appears healthy. Continue regular care.",
    "Blueberry___healthy": "Plant appears healthy.",
    "Cherry_(including_sour)___Powdery_mildew": "Apply sulfur or potassium bicarbonate spray. Improve air circulation.",
    "Cherry_(including_sour)___healthy": "Plant appears healthy.",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Apply strobilurin fungicide. Practice crop rotation.",
    "Corn_(maize)___Common_rust_": "Apply propiconazole fungicide. Plant resistant varieties next season.",
    "Corn_(maize)___Northern_Leaf_Blight": "Apply azoxystrobin fungicide at early tasseling. Use resistant hybrids.",
    "Corn_(maize)___healthy": "Plant appears healthy.",
    "Grape___Black_rot": "Remove mummified fruit. Apply mancozeb fungicide before and during wet weather.",
    "Grape___Esca_(Black_Measles)": "Prune infected wood. No chemical cure — remove severely affected vines.",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Apply copper-based fungicide. Improve canopy ventilation.",
    "Grape___healthy": "Plant appears healthy.",
    "Orange___Haunglongbing_(Citrus_greening)": "Remove infected trees. Control Asian citrus psyllid vector with insecticide.",
    "Peach___Bacterial_spot": "Apply copper hydroxide spray. Avoid overhead irrigation.",
    "Peach___healthy": "Plant appears healthy.",
    "Pepper,_bell___Bacterial_spot": "Apply copper-based bactericide. Rotate crops. Avoid working in wet fields.",
    "Pepper,_bell___healthy": "Plant appears healthy.",
    "Potato___Early_blight": "Apply chlorothalonil or mancozeb. Ensure proper spacing for air circulation.",
    "Potato___Late_blight": "URGENT: Apply metalaxyl fungicide immediately. Destroy infected plants. Do not compost.",
    "Potato___healthy": "Plant appears healthy.",
    "Raspberry___healthy": "Plant appears healthy.",
    "Soybean___healthy": "Plant appears healthy.",
    "Squash___Powdery_mildew": "Apply neem oil or sulfur spray weekly. Water at base, not overhead.",
    "Strawberry___Leaf_scorch": "Remove infected leaves. Apply captan fungicide. Avoid wet foliage.",
    "Strawberry___healthy": "Plant appears healthy.",
    "Tomato___Bacterial_spot": "Apply copper-based bactericide. Avoid overhead watering. Remove infected leaves.",
    "Tomato___Early_blight": "Apply mancozeb or chlorothalonil every 7-10 days. Mulch around base.",
    "Tomato___Late_blight": "URGENT: Apply metalaxyl or cymoxanil immediately. Destroy infected tissue.",
    "Tomato___Leaf_Mold": "Improve greenhouse ventilation. Apply chlorothalonil fungicide.",
    "Tomato___Septoria_leaf_spot": "Remove lower infected leaves. Apply mancozeb. Avoid wetting foliage.",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Apply neem oil or abamectin. Spray undersides of leaves. Increase humidity.",
    "Tomato___Target_Spot": "Apply azoxystrobin or pyraclostrobin fungicide. Improve air circulation.",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Remove infected plants immediately. Control whitefly vectors with imidacloprid.",
    "Tomato___Tomato_mosaic_virus": "Remove infected plants. Disinfect tools. Plant resistant varieties.",
    "Tomato___healthy": "Plant appears healthy. Continue regular care and monitoring.",
}

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
    treatment  = TREATMENT_MAP.get(label, "Consult your local Krishi Vigyan Kendra (KVK) for expert advice.")

    return {
        "label":       label,
        "crop":        crop,
        "disease":     disease,
        "is_healthy":  is_healthy,
        "confidence":  confidence,
        "treatment":   treatment,
        "severity":    "none" if is_healthy else ("urgent" if "URGENT" in treatment else "moderate"),
        "all_predictions": results,
    }
