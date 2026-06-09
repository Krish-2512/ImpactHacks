from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.disease.detector import predict
from backend.auth.dependencies import get_current_user

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/detect")
async def detect_disease(
    image: UploadFile = File(...),
    _user=Depends(get_current_user),
):
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WebP images accepted")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be under 10 MB")

    try:
        result = predict(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")

    return {"success": True, "result": result}
