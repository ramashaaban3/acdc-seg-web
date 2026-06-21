from pathlib import Path
import os

# =========================================================
# BASE PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# =========================================================
# DEFAULT MODELS
# =========================================================

DEFAULT_SEGMENTATION_MODEL = os.getenv("DEFAULT_SEGMENTATION_MODEL", "3d_unet")

DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")

DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")


# =========================================================
# SEGMENTATION MODEL DATASETS
# =========================================================
# Her segmentasyon modeli kendi JSON export klasörüne bağlanır.
#
# Şu an aktif ve çalışan model:
# - 3D U-Net
#
# 2D ResU-Net ve 3D ResU-Net için aynı JSON şemasıyla export alınca
# sadece aşağıdaki path'leri gerçek klasör adlarıyla güncellemek yeterli.
# =========================================================

SEGMENTATION_MODEL_DATASETS = {
    "3d_unet": DATA_DIR / "vqa_json_3d_unet_bplan_20260529_182119",
    # Şimdilik placeholder.
    # Gerçek 2D ResU-Net JSON klasörü hazır olunca burayı güncelleyeceğiz.
    "2d_resunet": DATA_DIR / "vqa_json_2d_resunet",
    # İleride 3D ResU-Net eklenecekse burası kullanılacak.
    "3d_resunet": DATA_DIR / "vqa_json_3d_resunet",
}


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================
# Eski kodlarda JSON_DATA_ROOT, PATIENTS_DIR, MANIFEST_PATH veya SUMMARY_PATH
# kullanılıyorsa bozulmasın diye 3D U-Net default path'i korunur.
# =========================================================

JSON_DATA_ROOT = SEGMENTATION_MODEL_DATASETS[DEFAULT_SEGMENTATION_MODEL]

PATIENTS_DIR = JSON_DATA_ROOT / "patients"
MANIFEST_PATH = JSON_DATA_ROOT / "manifest.json"
SUMMARY_PATH = JSON_DATA_ROOT / "summary_3d_unet.json"
