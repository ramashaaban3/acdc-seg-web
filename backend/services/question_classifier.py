# =========================================================
# QUESTION CLASSIFIER
# =========================================================

DIRECT_METRIC = "direct_metric"
CLINICAL_COMPARISON = "clinical_comparison"
CLINICAL_INTERPRETATION = "clinical_interpretation"
TECHNICAL_QC = "technical_qc"
ARTIFACT_INFO = "artifact_info"
UNKNOWN = "unknown"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_question(question: str) -> str:
    """
    Kullanıcı sorusunu VQA routing için sınıflandırır.

    Sınıflar:
    - direct_metric: EF, EDV, ESV gibi doğrudan metrik soruları
    - clinical_comparison: EF düşük mü, normal mi, LV dilate mi gibi eşik bazlı sorular
    - clinical_interpretation: klinik yorum / rapor / açıklama soruları
    - technical_qc: hata, QC, B planı, spacing, güvenilirlik
    - artifact_info: overlay, maske, segmentasyon görseli
    - unknown: varsayılan
    """

    q = question.casefold().strip()

    # -----------------------------------------------------
    # 1) Teknik/QC soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "hata", "fark", "güvenilir", "güven", "doğruluk",
        "performans", "qc", "kalite", "quality",
        "b plan", "spacing", "effective", "düzeltme",
        "voxel", "crop", "risk", "volume correction"
    ]):
        return TECHNICAL_QC

    # -----------------------------------------------------
    # 2) Artifact / görsel / maske soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "overlay", "maske", "mask", "görüntü", "image",
        "segmentasyon", "segmentation", "bölütleme", "görsel"
    ]):
        return ARTIFACT_INFO

    # -----------------------------------------------------
    # 3) Klinik yorum / açıklama soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "yorumla", "yorum", "klinik olarak", "rapor",
        "açıkla", "açıklama", "ne anlama", "anlamı",
        "interpret", "clinically", "clinical interpretation",
        "what does this mean", "report"
    ]):
        return CLINICAL_INTERPRETATION

    # -----------------------------------------------------
    # 4) Klinik karşılaştırma / eşik soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "normal mi", "düşük mü", "yüksek mi", "azalmış mı",
        "korunmuş mu", "preserved", "reduced", "low",
        "normal", "enlarged", "dilate", "dilated",
        "genişlemiş", "dilate mi", "lv dilate",
        "sistolik fonksiyon", "systolic function"
    ]):
        return CLINICAL_COMPARISON

    # -----------------------------------------------------
    # 5) Doğrudan metrik soruları
    # -----------------------------------------------------
    if _contains_any(q, [
        "ef", "ejeksiyon", "fraksiyon", "ejection fraction",
        "edv", "esv", "son-diyastol", "son-sistol",
        "diyastol", "sistol", "hacim", "volume",
        "kaç", "kaç ml", "değeri nedir", "value"
    ]):
        return DIRECT_METRIC

    return UNKNOWN