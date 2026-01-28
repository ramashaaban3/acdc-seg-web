from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import nibabel as nib

from acdc_app.pipeline.data_io import load_patient_files
from acdc_app.pipeline.inference import (
    InferenceConfig,
    load_resunet2d_state_dict,
    predict_mask_volume_original_space,
)
from acdc_app.pipeline.metrics import voxel_volume_ml, compute_edv_esv_ef
from acdc_app.pipeline.render import save_overlay_png


@dataclass
class PipelinePaths:
    demo_root: Path
    ckpt_path: Path
    out_dir: Path


def run_pipeline(
    patient_id: str,
    paths: PipelinePaths,
    cfg: InferenceConfig,
    lv_label: int = 3,
    display_patient_id: str | None = None,
) -> Dict[str, Any]:
    """
    patient_id: gerçek klasör adı (patient110 gibi)
    display_patient_id: UI'da göstermek istediğin ad (Patient 2 gibi)
    """
    pf = load_patient_files(paths.demo_root, patient_id)

    ed_img = nib.load(str(pf.ed_image_path))
    es_img = nib.load(str(pf.es_image_path))

    ed_vol = ed_img.get_fdata().astype(np.float32)  # (H,W,Z)
    es_vol = es_img.get_fdata().astype(np.float32)

    model = load_resunet2d_state_dict(paths.ckpt_path, cfg)

    ed_mask = predict_mask_volume_original_space(model, ed_vol, cfg)
    es_mask = predict_mask_volume_original_space(model, es_vol, cfg)

    vml = voxel_volume_ml(ed_img)
    edv, esv, ef = compute_edv_esv_ef(ed_mask, es_mask, vml, lv_label=lv_label)

    # Görsel için orta slice
    z_mid = ed_vol.shape[2] // 2

    # çıktı klasörü GERÇEK ID ile kalmalı
    ed_overlay_path = paths.out_dir / patient_id / "ed_overlay.png"
    es_overlay_path = paths.out_dir / patient_id / "es_overlay.png"
    save_overlay_png(ed_vol[..., z_mid], ed_mask[..., z_mid], ed_overlay_path, title=f"{patient_id} ED overlay")
    save_overlay_png(es_vol[..., z_mid], es_mask[..., z_mid], es_overlay_path, title=f"{patient_id} ES overlay")

    # UI etiketi: display varsa onu göster
    shown_id = display_patient_id or patient_id

    return {
        "patient_id": shown_id,                # UI tarafında görünen
        "real_patient_id": patient_id,         # backend tarafında gerçek
        "edv_ml": float(edv),
        "esv_ml": float(esv),
        "ef_percent": float(ef),
        "ed_overlay_png": str(ed_overlay_path),
        "es_overlay_png": str(es_overlay_path),
    }
