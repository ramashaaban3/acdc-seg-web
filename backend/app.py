from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from acdc_app.run_pipeline import run_pipeline, PipelinePaths
from acdc_app.pipeline.inference import InferenceConfig
from acdc_app.pipeline.data_io import list_patients


app = FastAPI(title="ACDC Segmentation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Proje yolları ---
BACKEND_ROOT = Path(__file__).resolve().parent          # backend/
DEMO_ROOT    = BACKEND_ROOT / "data" / "demo"
CKPT_PATH    = BACKEND_ROOT / "models" / "best_resunet2d_acdc.pt"
OUT_DIR      = BACKEND_ROOT / "outputs"

paths = PipelinePaths(demo_root=DEMO_ROOT, ckpt_path=CKPT_PATH, out_dir=OUT_DIR)
cfg   = InferenceConfig(device="cpu", num_classes=4, out_hw=(256, 256))

# outputs klasörünü URL'den servis et: /outputs/...
OUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(OUT_DIR)), name="outputs")


def _ensure_ready() -> None:
    """Demo klasörü ve checkpoint gibi kritik bağımlılıkları kontrol et."""
    if not DEMO_ROOT.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Demo root not found: {DEMO_ROOT} (backend/data/demo klasörünü oluşturup patient klasörlerini koymalısın.)",
        )
    if not CKPT_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Checkpoint not found: {CKPT_PATH} (best_resunet2d_acdc.pt dosyasını backend/models içine koymalısın.)",
        )


@app.get("/")
def root():
    return {"ok": True, "endpoints": ["/patients", "/predict?patient_id=patient101"]}


@app.get("/patients")
def patients() -> List[Dict[str, str]]:
    """
    UI tarafı için: Patient 1..N isimleri + gerçek id
    """
    _ensure_ready()
    pids = sorted(list_patients(DEMO_ROOT))
    if not pids:
        raise HTTPException(status_code=500, detail=f"No patients found under: {DEMO_ROOT}")
    return [{"patient_id": f"Patient {i+1}", "real_patient_id": pid} for i, pid in enumerate(pids)]


@app.get("/predict")
def predict(
    request: Request,
    patient_id: str = Query(..., description="real id: patient101 OR display id: Patient 1"),
) -> Dict[str, Any]:
    _ensure_ready()

    pids = sorted(list_patients(DEMO_ROOT))
    if not pids:
        raise HTTPException(status_code=500, detail=f"No patients found under: {DEMO_ROOT}")

    # Display mapping: patient101 -> Patient 1
    display_ids = {pid: f"Patient {i+1}" for i, pid in enumerate(pids)}
    reverse_display = {v: k for k, v in display_ids.items()}

    # Kullanıcı "Patient 1" yazarsa real id’ye çevir
    real_patient_id = reverse_display.get(patient_id, patient_id)

    if real_patient_id not in pids:
        raise HTTPException(status_code=404, detail=f"Unknown patient_id: {patient_id}")

    display_label = display_ids[real_patient_id]

    result = run_pipeline(
        patient_id=real_patient_id,
        paths=paths,
        cfg=cfg,
        lv_label=3,
        display_patient_id=display_label,   # UI’da bunu göstereceğiz
    )

    # Dosya yolu yerine URL üret (StaticFiles mount’u sayesinde çalışır)
    # result içinde: ed_overlay_png, es_overlay_png dosya yolları var.
    # Biz onları UI'da kullanmayalım, url dönelim:
    result.pop("ed_overlay_png", None)
    result.pop("es_overlay_png", None)

    # base url (örn http://127.0.0.1:8000/)
    base = str(request.base_url).rstrip("/")

    result["ed_overlay_url"] = f"{base}/outputs/{real_patient_id}/ed_overlay.png"
    result["es_overlay_url"] = f"{base}/outputs/{real_patient_id}/es_overlay.png"

    # İstersen ikisini de net dön:
    result["patient_id"] = display_label
    result["real_patient_id"] = real_patient_id

    return result
