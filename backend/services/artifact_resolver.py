from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
OVERLAYS_DIR = STATIC_DIR / "overlays"


def _build_url_if_exists(file_path: Path, public_url: str):
    if file_path.exists():
        return public_url
    return None


def build_artifact_urls(patient_id: str, segmentation_model: str = "3d_unet") -> dict:
    """
    Hasta ve segmentasyon modeline göre overlay/mask URL'lerini üretir.

    Beklenen dosya isimleri:
    - patient100_ed_overlay.png
    - patient100_es_overlay.png
    - patient100_ed_mask.png
    - patient100_es_mask.png
    """

    segmentation_model = (segmentation_model or "3d_unet").strip().lower()
    patient_id = patient_id.strip()

    model_dir = OVERLAYS_DIR / segmentation_model

    ed_overlay_name = f"{patient_id}_ed_overlay.png"
    es_overlay_name = f"{patient_id}_es_overlay.png"
    ed_mask_name = f"{patient_id}_ed_mask.png"
    es_mask_name = f"{patient_id}_es_mask.png"

    ed_overlay_path = model_dir / ed_overlay_name
    es_overlay_path = model_dir / es_overlay_name
    ed_mask_path = model_dir / ed_mask_name
    es_mask_path = model_dir / es_mask_name

    return {
        "overlay_ed_url": _build_url_if_exists(
            ed_overlay_path, f"/static/overlays/{segmentation_model}/{ed_overlay_name}"
        ),
        "overlay_es_url": _build_url_if_exists(
            es_overlay_path, f"/static/overlays/{segmentation_model}/{es_overlay_name}"
        ),
        "mask_ed_url": _build_url_if_exists(
            ed_mask_path, f"/static/overlays/{segmentation_model}/{ed_mask_name}"
        ),
        "mask_es_url": _build_url_if_exists(
            es_mask_path, f"/static/overlays/{segmentation_model}/{es_mask_name}"
        ),
    }
