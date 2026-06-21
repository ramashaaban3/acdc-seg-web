# =========================================================
# CLINICAL RULES
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


def classify_ef(ef_percent):
    """
    Basit EF sınıflandırması.

    Bu sınıflandırma tanı koymak için değil,
    otomatik segmentasyon çıktısını klinik olarak daha anlaşılır
    ifade etmek için kullanılır.
    """

    ef = _safe_float(ef_percent)

    if ef is None:
        return {
            "category": "unknown",
            "label_tr": "EF değeri yorumlanamadı.",
            "short_label_tr": "yorumlanamayan EF aralığı",
            "label_en": "EF could not be interpreted."
        }
    # Azalmış sistolik fonksiyon: genellikle EF < 40% olarak kabul edilir
    if ef < 40:
        return {
            "category": "reduced",
            "label_tr": "EF değeri azalmış sistolik fonksiyon aralığında değerlendirilebilir.",
            "short_label_tr": "azalmış sistolik fonksiyon aralığı",
            "label_en": "EF is in the reduced systolic function range."
        }

    if ef < 50:
        return {
            "category": "mildly_reduced",
            "label_tr": "EF değeri hafif azalmış sistolik fonksiyon aralığında değerlendirilebilir.",
            "short_label_tr": "hafif azalmış sistolik fonksiyon aralığı",
            "label_en": "EF is in the mildly reduced systolic function range."
        }

    return {
        "category": "preserved",
        "answer_tr": "EF değeri korunmuş sistolik fonksiyon aralığında değerlendirilebilir.",
        "short_label_tr": "korunmuş sistolik fonksiyon aralığı",
        "label_en": "EF is in the preserved systolic function range."
    }

#LV dilatasyonu yani sol ventrikül genişlemesiyle ilgili kesin bir sınıflandırma yapmak için genellikle BSA'ya indekslenmiş LVEDV (LVEDVi) değerine ihtiyaç vardır. Ancak bu JSON sürümünde bu bilgi bulunmadığı için, sadece EDV değerine dayanarak kesin bir dilatasyon sınıflandırması yapmak mümkün değildir. Bu nedenle, bu fonksiyon yalnızca EDV değerini raporlar ve dilatasyon hakkında kesin bir yorum yapmaz.
def assess_lv_enlargement(edv_ml, indexed_edv_ml=None, sex=None):
    """
    LV dilatasyon değerlendirmesi için güvenli kural.

    Bu projedeki JSON'da BSA, cinsiyet ve LVEDVi bulunmadığı için
    ilk sürümde kesin LV dilatasyonu sınıflandırması yapılmaz.
    """

    edv = _safe_float(edv_ml)

    return {
        "category": "not_classified",
        "answer_tr": (
            f"LV EDV değeri {_fmt(edv)} ml olarak hesaplanmıştır. "
            "Ancak hastaya ait BSA'ya indekslenmiş LV hacmi, cinsiyet ve yaş bilgisi "
            "bulunmadığı için sol ventrikül dilatasyonu açısından kesin bir sınıflandırma yapılmamıştır."
        ),
        "used_metrics": {
            "clinical_metrics.prediction.edv_ml": edv_ml,
            "indexed_edv_ml": indexed_edv_ml,
            "sex": sex
        }
    }


def generate_clinical_comparison_answer(result_data: dict, question: str):
    """
    EF düşük mü, EF normal mi, LV dilate mi gibi basit klinik karşılaştırma
    sorularını kural tabanlı olarak cevaplar.
    """

    q = question.casefold().strip()

    patient_id = result_data.get("patient_id", "unknown_patient")

    clinical_metrics = result_data.get("clinical_metrics", {})
    prediction = clinical_metrics.get("prediction", {})

    edv = prediction.get("edv_ml")
    esv = prediction.get("esv_ml")
    ef = prediction.get("ef_percent")

    quality_control = result_data.get("quality_control", {})
    error_flag = quality_control.get("error_flag", "unknown")

    # -----------------------------------------------------
    # EF / sistolik fonksiyon soruları
    # -----------------------------------------------------
    if (
        "ef" in q
        or "ejeksiyon" in q
        or "fraksiyon" in q
        or "sistolik" in q
        or "systolic" in q
        or "preserved" in q
        or "reduced" in q
        or "ef düşük" in q
        or "ejeksiyon fraksiyonu düşük" in q
        or "sistolik fonksiyon düşük" in q
        or "ef az" in q
        or "ef normal" in q
        or "ejeksiyon fraksiyonu normal" in q
        or "sistolik fonksiyon normal" in q
    ):
        ef_info = classify_ef(ef)

        answer = (
            f"{patient_id} hastasında EF değeri %{_fmt(ef)} olarak hesaplanmıştır. "
            f"Bu değer, kullanılan EF sınıflandırmasına göre {ef_info['short_label_tr']} içindedir. "
            "Bu yorum otomatik segmentasyon çıktısından türetilmiştir ve tek başına klinik tanı yerine geçmez."
)

        if error_flag == "high":
            answer += " Bu hastada hata bayrağı yüksek olduğu için sonuçlar dikkatli yorumlanmalıdır."
        elif error_flag == "moderate":
            answer += " Bu hastada hata bayrağı orta düzeydedir; sonuçlar klinik bağlamla birlikte değerlendirilmelidir."

        return {
            "answer": (
        f"{patient_id} hastası için {lv_info['answer_tr']} "
        "Bu nedenle sistem bu aşamada yalnızca ölçülen hacim değerini raporlar; "
        "kesin klinik karar uzman değerlendirmesiyle verilmelidir."
    ),
    "answer_type": "clinical_comparison_lv_volume",
    "source": "clinical_rules_v1",
    "confidence": "medium",
    "used_metrics": lv_info["used_metrics"],
    "rule_result": {
        "category": lv_info["category"]
    }
        }

    # -----------------------------------------------------
    # LV dilatasyon / LV enlargement soruları
    # -----------------------------------------------------
    if (
        "lv dilate" in q
        or "dilate" in q
        or "dilated" in q
        or "enlarged" in q
        or "genişlemiş" in q
        or "sol ventrikül hacmi" in q
        or "left ventricle enlarged" in q
    ):
        lv_info = assess_lv_enlargement(edv)

        return {
            "answer": (
                f"{patient_id} hastası için {lv_info['answer_tr']} "
                "Bu nedenle sistem yalnızca hacim değerini raporlar, kesin dilatasyon kararı vermez."
            ),
            "answer_type": "clinical_comparison_lv_volume",
            "source": "clinical_rules_v1",
            "confidence": "medium",
            "used_metrics": lv_info["used_metrics"],
            "rule_result": {
                "category": lv_info["category"]
            }
        }

    # Eğer soru EF veya LV dilatasyon sorusu olarak yakalanmazsa, sistem genel özet cevabı döndürüyor
    # -----------------------------------------------------
    # Varsayılan klinik karşılaştırma cevabı
    # -----------------------------------------------------
    ef_info = classify_ef(ef)

    return {
        "answer": (
            f"{patient_id} hastasında LV EDV {_fmt(edv)} ml, LV ESV {_fmt(esv)} ml "
            f"ve EF %{_fmt(ef)} olarak hesaplanmıştır. {ef_info['label_tr']} "
            "Bu çıktı otomatik segmentasyon sonuçlarına dayalıdır."
        ),
        "answer_type": "clinical_comparison_summary",
        "source": "clinical_rules_v1",
        "confidence": "medium",
        "used_metrics": {
            "clinical_metrics.prediction.edv_ml": edv,
            "clinical_metrics.prediction.esv_ml": esv,
            "clinical_metrics.prediction.ef_percent": ef
        },
        "rule_result": ef_info
    }