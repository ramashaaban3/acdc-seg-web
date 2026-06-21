from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.artifact_resolver import build_artifact_urls

from config import (
    BASE_DIR,
    JSON_DATA_ROOT,
    SEGMENTATION_MODEL_DATASETS,
    DEFAULT_SEGMENTATION_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
)
from schemas.vqa_schema import VQARequest, VQAResponse
from services.result_loader import ResultLoader, ResultNotFoundError
from services.vqa_orchestrator import answer_question

app = FastAPI(
    title="Cardiac MRI VQA Backend",
    description="Backend API for cardiac MRI clinical metrics, segmentation outputs and LLM-based VQA.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Default loader: eski endpointler ve /patients için 3D U-Net kullanılır.
result_loader = ResultLoader(JSON_DATA_ROOT)


# =========================================================
# HELPER FUNCTIONS
# =========================================================


def round_metric(value, ndigits=2):
    """
    Frontend'de gösterilecek sayısal değerleri okunabilir hale getirir.
    None değerleri bozmadan döndürür.
    """

    if value is None:
        return None

    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return value


def get_result_loader_for_model(segmentation_model: str):
    """
    Kullanıcının seçtiği segmentasyon modeline göre ilgili JSON klasörünü okuyan loader döndürür.

    Örnek:
    - 3d_unet -> vqa_json_3d_unet_bplan_20260529_182119
    - 2d_resunet -> ileride eklenecek JSON klasörü
    - 3d_resunet -> ileride eklenecek JSON klasörü
    """

    model_key = segmentation_model or DEFAULT_SEGMENTATION_MODEL

    if model_key not in SEGMENTATION_MODEL_DATASETS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported segmentation model: {model_key}"
        )

    data_root = SEGMENTATION_MODEL_DATASETS[model_key]

    if not data_root.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Data folder for segmentation model '{model_key}' was not found. "
                f"Expected path: {data_root}"
            ),
        )

    return ResultLoader(data_root)


def build_frontend_payload(result_data: dict):
    """
    Hasta JSON'undan frontend'in doğrudan kullanabileceği alanları hazırlar.

    Frontend bu alanları kullanarak:
    - EDV / ESV / EF kartlarını
    - hata kartlarını
    - kalite kontrol bilgisini
    - overlay alanını
    gösterebilir.
    """

    clinical_metrics = result_data.get("clinical_metrics", {})
    prediction = clinical_metrics.get("prediction", {})
    reference = clinical_metrics.get("reference", {})
    absolute_errors = clinical_metrics.get("absolute_errors", {})

    quality_control = result_data.get("quality_control", {})
    phase_info = result_data.get("phase_info", {})
    artifacts = result_data.get("artifacts", {})

    edv = prediction.get("edv_ml")
    esv = prediction.get("esv_ml")
    ef = prediction.get("ef_percent")

    frontend_clinical_metrics = {
        "prediction": {
            "edv_ml": round_metric(edv),
            "esv_ml": round_metric(esv),
            "ef_percent": round_metric(ef),
        },
        "reference": {
            "edv_ml": round_metric(reference.get("edv_ml")),
            "esv_ml": round_metric(reference.get("esv_ml")),
            "ef_percent": round_metric(reference.get("ef_percent")),
        },
        "absolute_errors": {
            "edv_ml": round_metric(absolute_errors.get("edv_ml")),
            "esv_ml": round_metric(absolute_errors.get("esv_ml")),
            "ef_percent": round_metric(absolute_errors.get("ef_percent")),
        },
    }

    frontend_artifacts = {
        "overlay_ed_url": artifacts.get("overlay_ed_url")
        or artifacts.get("ed_overlay"),
        "overlay_es_url": artifacts.get("overlay_es_url")
        or artifacts.get("es_overlay"),
        "mask_ed_url": artifacts.get("mask_ed_url") or artifacts.get("ed_pred_mask"),
        "mask_es_url": artifacts.get("mask_es_url") or artifacts.get("es_pred_mask"),
    }

    ui_payload = {
        "metric_cards": [
            {
                "label": "EDV",
                "title": "End-Diastolic Volume",
                "value": round_metric(edv),
                "unit": "ml",
                "description": "Sol ventrikül son-diyastol hacmi",
            },
            {
                "label": "ESV",
                "title": "End-Systolic Volume",
                "value": round_metric(esv),
                "unit": "ml",
                "description": "Sol ventrikül son-sistol hacmi",
            },
            {
                "label": "EF",
                "title": "Ejection Fraction",
                "value": round_metric(ef),
                "unit": "%",
                "description": "Ejeksiyon fraksiyonu",
            },
        ],
        "error_cards": [
            {
                "label": "EDV Error",
                "value": round_metric(absolute_errors.get("edv_ml")),
                "unit": "ml",
            },
            {
                "label": "ESV Error",
                "value": round_metric(absolute_errors.get("esv_ml")),
                "unit": "ml",
            },
            {
                "label": "EF Error",
                "value": round_metric(absolute_errors.get("ef_percent")),
                "unit": "percentage points",
            },
        ],
        "warning": (
            "Bu sonuçlar otomatik segmentasyon çıktısından türetilmiştir "
            "ve uzman klinik değerlendirmesinin yerine geçmez."
        ),
    }

    return {
        "clinical_metrics": frontend_clinical_metrics,
        "quality_control": {
            "status": quality_control.get("status"),
            "error_flag": quality_control.get("error_flag"),
            "has_crop_risk": quality_control.get("has_crop_risk"),
        },
        "phase_info": {
            "ed_frame": phase_info.get("ed_frame"),
            "es_frame": phase_info.get("es_frame"),
        },
        "artifacts": frontend_artifacts,
        "ui": ui_payload,
    }


def get_model_statuses():
    """
    Backend'de tanımlı segmentasyon modeli klasörlerinin mevcut olup olmadığını döndürür.
    Bu bilgi /health endpoint'inde gösterilir.
    """

    statuses = {}

    for model_key, path in SEGMENTATION_MODEL_DATASETS.items():
        statuses[model_key] = {
            "data_root": str(path),
            "available": path.exists(),
            "patients_dir_exists": (path / "patients").exists(),
        }

    return statuses


# =========================================================
# ROUTES
# =========================================================


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Cardiac MRI VQA Backend",
        "version": "2.0.0",
        "default_segmentation_model": DEFAULT_SEGMENTATION_MODEL,
        "default_llm_provider": DEFAULT_LLM_PROVIDER,
        "default_llm_model": DEFAULT_LLM_MODEL,
        "endpoints": [
            "/health",
            "/patients",
            "/patients/{patient_id}/results",
            "/summary",
            "/vqa/ask",
        ],
    }


@app.get("/health")
def health_check():
    status = result_loader.health_status()

    return {
        "status": "ok",
        "message": "Cardiac MRI VQA backend is running.",
        "default_segmentation_model": DEFAULT_SEGMENTATION_MODEL,
        "default_llm_provider": DEFAULT_LLM_PROVIDER,
        "default_llm_model": DEFAULT_LLM_MODEL,
        **status,
        "segmentation_model_statuses": get_model_statuses(),
    }


@app.get("/patients")
def get_patients():
    """
    Varsayılan olarak 3D U-Net JSON klasöründeki hasta listesini döndürür.
    Frontend hasta seçiminde bunu kullanır.
    """

    try:
        return result_loader.list_patients()
    except ResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/patients/{patient_id}/results")
def get_patient_result(patient_id: str):
    """
    Varsayılan 3D U-Net JSON sonucunu döndürür.
    """

    try:
        return result_loader.load_patient_result(patient_id)
    except ResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/summary")
def get_summary():
    """
    Varsayılan 3D U-Net özet dosyasını döndürür.
    """

    try:
        return result_loader.load_summary()
    except ResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/vqa/ask", response_model=VQAResponse)
def ask_vqa(request: VQARequest):
    """
    Full LLM VQA endpointi.

    İş akışı:
    1. Frontend'den hasta, soru, segmentasyon modeli ve LLM modeli alınır.
    2. Seçilen segmentasyon modelinin JSON klasörü okunur.
    3. Hasta sonucu LLM context'e dönüştürülür.
    4. LLM doğal dil cevabı üretir.
    5. Frontend için metrik kartları, hata değerleri, QC ve artifact alanları eklenir.
    """

    selected_segmentation_model = (
        request.segmentation_model or DEFAULT_SEGMENTATION_MODEL
    )
    selected_llm_provider = request.llm_provider or DEFAULT_LLM_PROVIDER
    selected_llm_model = request.llm_model or DEFAULT_LLM_MODEL

    selected_loader = get_result_loader_for_model(selected_segmentation_model)

    try:
        result_data = selected_loader.load_patient_result(request.patient_id)
    except ResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Not:
    # llm_provider ve llm_model alanlarını bir sonraki adımda orchestrator/engine tarafına bağlayacağız.
    # Şimdilik backend cevabına ekliyoruz ve frontend için hazır tutuyoruz.
    orchestrated_answer = answer_question(
        result_data=result_data,
        question=request.question,
        mode=request.mode,
        llm_provider=selected_llm_provider,
        llm_model=selected_llm_model,
    )

    artifact_urls = build_artifact_urls(
        patient_id=selected_loader.normalize_patient_id(request.patient_id),
        segmentation_model=selected_segmentation_model,
    )

    frontend_payload = build_frontend_payload(result_data)

    # Static overlay dosyaları varsa JSON içindeki boş artifact alanlarının üzerine yazılır.
    frontend_payload["artifacts"] = artifact_urls

    return {
        "patient_id": selected_loader.normalize_patient_id(request.patient_id),
        "question": request.question,
        "vqa_version": orchestrated_answer["vqa_version"],
        "mode": orchestrated_answer["mode_used"],
        "question_type": orchestrated_answer["question_type"],
        "response": orchestrated_answer["response"],
        "segmentation_model": selected_segmentation_model,
        "llm_provider": selected_llm_provider,
        "llm_model": selected_llm_model,
        "clinical_metrics": frontend_payload["clinical_metrics"],
        "quality_control": frontend_payload["quality_control"],
        "phase_info": frontend_payload["phase_info"],
        "artifacts": frontend_payload["artifacts"],
        "ui": frontend_payload["ui"],
    }
