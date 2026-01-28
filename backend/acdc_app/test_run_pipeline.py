from pathlib import Path

from acdc_app.run_pipeline import run_pipeline, PipelinePaths
from acdc_app.pipeline.inference import InferenceConfig
from acdc_app.pipeline.data_io import list_patients


if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[1]   # backend/
    demo_root = backend_root / "data" / "demo"
    ckpt_path = backend_root / "models" / "best_resunet2d_acdc.pt"
    out_dir   = backend_root / "outputs"

    paths = PipelinePaths(demo_root=demo_root, ckpt_path=ckpt_path, out_dir=out_dir)

    patients = list_patients(demo_root)
    print("Patients (real):", patients)

    # Tek sefer üret
    display_ids = {pid: f"Patient {i + 1}" for i, pid in enumerate(patients)}
    print("Patients (display):", [display_ids[p] for p in patients])

    cfg = InferenceConfig(device="cpu", num_classes=4, out_hw=(256, 256))

    # Hepsini tek tek çalıştır
    for pid in patients:
        result = run_pipeline(pid, paths, cfg, lv_label=3, display_patient_id=display_ids[pid])
        print("RESULT:", result)
