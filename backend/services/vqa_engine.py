# =========================================================
# RULE-BASED VQA ENGINE
# =========================================================


def _safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value, ndigits=2):
    value = _safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:.{ndigits}f}"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _get_confidence_from_error_flag(error_flag: str):
    if error_flag == "high":
        return "low"
    if error_flag == "moderate":
        return "medium"
    return "high"


def _extract_context(result_data: dict):
    clinical_metrics = result_data.get("clinical_metrics", {})
    prediction = clinical_metrics.get("prediction", {})
    reference = clinical_metrics.get("reference", {})
    errors = clinical_metrics.get("absolute_errors", {})

    quality_control = result_data.get("quality_control", {})
    volume_correction = result_data.get("volume_correction", {})
    phase_info = result_data.get("phase_info", {})
    vqa_context = result_data.get("vqa_context", {})

    error_flag = quality_control.get("error_flag", "unknown")

    return {
        "patient_id": result_data.get("patient_id", "unknown_patient"),

        "edv": prediction.get("edv_ml"),
        "esv": prediction.get("esv_ml"),
        "ef": prediction.get("ef_percent"),

        "ref_edv": reference.get("edv_ml"),
        "ref_esv": reference.get("esv_ml"),
        "ref_ef": reference.get("ef_percent"),

        "err_edv": errors.get("edv_ml"),
        "err_esv": errors.get("esv_ml"),
        "err_ef": errors.get("ef_percent"),

        "quality_control": quality_control,
        "error_flag": error_flag,
        "confidence": _get_confidence_from_error_flag(error_flag),

        "volume_correction": volume_correction,
        "phase_info": phase_info,
        "vqa_context": vqa_context,
        "artifacts": result_data.get("artifacts", {}),
    }


def generate_rule_based_answer(result_data: dict, question: str):
    """
    3D U-Net B planı JSON çıktısına göre kural tabanlı VQA cevabı üretir.

    Bu engine şu soru tipleri için kullanılır:
    - EF / EDV / ESV gibi doğrudan metrik soruları
    - Referans / ground truth soruları
    - Hata / güvenilirlik / QC soruları
    - B planı / effective spacing soruları
    - ED / ES frame soruları
    - Overlay / maske bilgisi
    - LLM fallback durumu
    """

    q = question.casefold().strip()
    ctx = _extract_context(result_data)

    patient_id = ctx["patient_id"]

    edv = ctx["edv"]
    esv = ctx["esv"]
    ef = ctx["ef"]

    ref_edv = ctx["ref_edv"]
    ref_esv = ctx["ref_esv"]
    ref_ef = ctx["ref_ef"]

    err_edv = ctx["err_edv"]
    err_esv = ctx["err_esv"]
    err_ef = ctx["err_ef"]

    error_flag = ctx["error_flag"]
    confidence = ctx["confidence"]

    # -----------------------------------------------------
    # EF soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "ef",
        "ejeksiyon",
        "fraksiyon",
        "ejection fraction"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için 3D U-Net tahminine göre "
                f"ejeksiyon fraksiyonu (EF) %{_fmt(ef)} olarak hesaplanmıştır."
            ),
            "answer_type": "ef_information",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "clinical_metrics.prediction.ef_percent": ef
            },
        }

    # -----------------------------------------------------
    # EDV soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "edv",
        "son-diyastol",
        "diyastol",
        "end-diastolic"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için sol ventrikül son-diyastol hacmi "
                f"(LV EDV) {_fmt(edv)} ml olarak hesaplanmıştır."
            ),
            "answer_type": "edv_information",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "clinical_metrics.prediction.edv_ml": edv
            },
        }

    # -----------------------------------------------------
    # ESV soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "esv",
        "son-sistol",
        "sistol",
        "end-systolic"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için sol ventrikül son-sistol hacmi "
                f"(LV ESV) {_fmt(esv)} ml olarak hesaplanmıştır."
            ),
            "answer_type": "esv_information",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "clinical_metrics.prediction.esv_ml": esv
            },
        }

    # -----------------------------------------------------
    # Tüm klinik metrikleri birlikte isteyen sorular
    # -----------------------------------------------------
    if _contains_any(q, [
        "metrik",
        "metrikler",
        "değerler",
        "parametre",
        "parametreler",
        "ölçüm",
        "ölçümler",
        "sonuç",
        "edv esv ef",
        "edv, esv",
        "hepsi",
        "tüm"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için 3D U-Net tahminine göre "
                f"LV EDV {_fmt(edv)} ml, LV ESV {_fmt(esv)} ml ve "
                f"EF %{_fmt(ef)} olarak hesaplanmıştır."
            ),
            "answer_type": "clinical_metrics_summary",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "clinical_metrics.prediction.edv_ml": edv,
                "clinical_metrics.prediction.esv_ml": esv,
                "clinical_metrics.prediction.ef_percent": ef,
            },
        }

    # -----------------------------------------------------
    # Klinik yorum fallback
    # -----------------------------------------------------
    if _contains_any(q, [
        "yorum",
        "yorumla",
        "klinik",
        "değerlendir",
        "açıkla",
        "rapor",
        "anlam",
        "ne anlama"
    ]):
        summary_tr = ctx["vqa_context"].get("summary_tr")

    
        answer = (
                f"{patient_id} hastası için LV EDV {_fmt(edv)} ml, "
                f"LV ESV {_fmt(esv)} ml ve EF %{_fmt(ef)} olarak hesaplanmıştır. "
                "Bu sonuç otomatik segmentasyon çıktısına dayalıdır ve uzman klinik değerlendirmesinin yerine geçmez."
            )

        if error_flag == "high":
            answer += " Bu hastada hata bayrağı yüksek olduğu için sonuçlar dikkatli yorumlanmalıdır."
        elif error_flag == "moderate":
            answer += " Bu hastada hata bayrağı orta düzeydedir; sonuçlar klinik bağlamla birlikte değerlendirilmelidir."

        return {
            "answer": answer,
            "answer_type": "clinical_interpretation_fallback",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "vqa_context.summary_tr": summary_tr,
                "quality_control.error_flag": error_flag,
            },
        }

    # -----------------------------------------------------
    # Referans / ground truth soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "ground truth",
        "referans",
        "gerçek",
        "gt",
        "etiket"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için referans değerlere göre "
                f"LV EDV {_fmt(ref_edv)} ml, LV ESV {_fmt(ref_esv)} ml ve "
                f"EF %{_fmt(ref_ef)} olarak hesaplanmıştır."
            ),
            "answer_type": "reference_metrics",
            "source": "rule_based_v1",
            "confidence": "high",
            "used_metrics": {
                "clinical_metrics.reference.edv_ml": ref_edv,
                "clinical_metrics.reference.esv_ml": ref_esv,
                "clinical_metrics.reference.ef_percent": ref_ef,
            },
        }

    # -----------------------------------------------------
    # Hata / güvenilirlik / performans soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "hata",
        "fark",
        "güven",
        "güvenilir",
        "doğruluk",
        "performans",
        "absolute",
        "abs"
    ]):
        return {
            "answer": (
                f"{patient_id} hastası için mutlak hata değerleri: "
                f"EDV {_fmt(err_edv)} ml, ESV {_fmt(err_esv)} ml ve "
                f"EF %{_fmt(err_ef)} olarak hesaplanmıştır. "
                f"Hata bayrağı: {error_flag}."
            ),
            "answer_type": "error_summary",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "clinical_metrics.absolute_errors.edv_ml": err_edv,
                "clinical_metrics.absolute_errors.esv_ml": err_esv,
                "clinical_metrics.absolute_errors.ef_percent": err_ef,
                "quality_control.error_flag": error_flag,
            },
        }

    # -----------------------------------------------------
    # QC / crop risk soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "qc",
        "kalite",
        "quality",
        "crop",
        "risk",
        "kontrol"
    ]):
        qc = ctx["quality_control"]
        qc_status = qc.get("status", "unknown")
        has_crop_risk = qc.get("has_crop_risk", None)

        return {
            "answer": (
                f"{patient_id} hastası için kalite kontrol durumu {qc_status}. "
                f"Crop risk bilgisi: {has_crop_risk}. "
                f"Hata bayrağı: {error_flag}."
            ),
            "answer_type": "quality_control_info",
            "source": "rule_based_v1",
            "confidence": confidence,
            "used_metrics": {
                "quality_control.status": qc_status,
                "quality_control.has_crop_risk": has_crop_risk,
                "quality_control.error_flag": error_flag,
            },
        }

    # -----------------------------------------------------
    # B planı / effective spacing / volume correction soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "b plan",
        "spacing",
        "effective",
        "düzeltme",
        "hacim düzelt",
        "voxel",
        "volume correction"
    ]):
        vc = ctx["volume_correction"]

        enabled = vc.get("enabled")
        method = vc.get("method")
        eff_spacing = vc.get("effective_spacing_mm", {})
        eff_voxel = vc.get("effective_voxel_volume_ml")
        ratios = vc.get("gt_consistency_ratios", {})

        return {
            "answer": (
                f"{patient_id} hastasında hacim hesabı için {method} yöntemi uygulanmıştır. "
                f"Effective spacing değerleri "
                f"x={_fmt(eff_spacing.get('x'), 4)}, "
                f"y={_fmt(eff_spacing.get('y'), 4)}, "
                f"z={_fmt(eff_spacing.get('z'), 4)} mm; "
                f"effective voxel hacmi {_fmt(eff_voxel, 6)} ml'dir. "
                f"GT tutarlılık oranları EDV için "
                f"{_fmt(ratios.get('edv_original_to_corrected_processed'), 4)}, "
                f"ESV için {_fmt(ratios.get('esv_original_to_corrected_processed'), 4)} olarak hesaplanmıştır."
            ),
            "answer_type": "volume_correction_info",
            "source": "rule_based_v1",
            "confidence": "high",
            "used_metrics": {
                "volume_correction.enabled": enabled,
                "volume_correction.method": method,
                "volume_correction.effective_spacing_mm": eff_spacing,
                "volume_correction.effective_voxel_volume_ml": eff_voxel,
                "volume_correction.gt_consistency_ratios": ratios,
            },
        }

    # -----------------------------------------------------
    # ED / ES frame soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "ed frame",
        "es frame",
        "faz",
        "frame"
    ]):
        phase_info = ctx["phase_info"]
        ed_frame = phase_info.get("ed_frame")
        es_frame = phase_info.get("es_frame")

        return {
            "answer": (
                f"{patient_id} hastasında ED fazı frame {ed_frame}, "
                f"ES fazı frame {es_frame} olarak kullanılmıştır."
            ),
            "answer_type": "phase_information",
            "source": "rule_based_v1",
            "confidence": "high",
            "used_metrics": {
                "phase_info.ed_frame": ed_frame,
                "phase_info.es_frame": es_frame,
            },
        }

    # -----------------------------------------------------
    # Overlay / maske / segmentasyon görseli soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "overlay",
        "maske",
        "mask",
        "görüntü",
        "image",
        "segmentasyon",
        "bölütleme",
        "görsel"
    ]):
        artifacts = ctx["artifacts"]

        return {
            "answer": (
                "Bu JSON sürümünde ED/ES tahmin maskesi ve overlay dosya yolları için alanlar ayrılmıştır; "
                "ancak mevcut export aşamasında bu alanlar boş bırakılmıştır. "
                "Şu an VQA sistemi klinik metrikler üzerinden cevap üretmektedir."
            ),
            "answer_type": "artifact_information",
            "source": "rule_based_v1",
            "confidence": "medium",
            "used_metrics": {
                "artifacts": artifacts
            },
        }

    # -----------------------------------------------------
    # Varsayılan cevap
    # -----------------------------------------------------
    return {
        "answer": (
            f"{patient_id} hastası için temel klinik sonuçlar: "
            f"LV EDV {_fmt(edv)} ml, LV ESV {_fmt(esv)} ml ve EF %{_fmt(ef)}. "
            "Daha ayrıntılı bilgi için EF, EDV, ESV, hata, klinik yorum, kalite kontrol veya B planı hakkında soru sorabilirsiniz."
        ),
        "answer_type": "default_summary",
        "source": "rule_based_v1",
        "confidence": confidence,
        "used_metrics": {
            "clinical_metrics.prediction.edv_ml": edv,
            "clinical_metrics.prediction.esv_ml": esv,
            "clinical_metrics.prediction.ef_percent": ef,
        },
    }