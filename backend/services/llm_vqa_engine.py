# =========================================================
# LLM VQA ENGINE - FULL LLM VERSION
# =========================================================

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from config import DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL
from services.llm_prompt_builder import build_llm_messages, build_llm_context

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_LLM_MODEL)


def _extract_json(text: str) -> dict:
    """
    LLM cevabını JSON olarak ayrıştırır.

    Normalde modelden sadece JSON bekliyoruz.
    Ancak model yanlışlıkla JSON dışı açıklama üretirse,
    ilk { ... } bloğunu yakalamayı dener.
    """

    if not text:
        raise ValueError("LLM response is empty.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response does not contain valid JSON.")

        return json.loads(text[start : end + 1])


def _normalize_llm_payload(payload: dict, context: dict) -> dict:
    """
    LLM cevabında eksik alan varsa API'nin stabil kalması için tamamlar.

    Bu fonksiyon klinik cevap üretmez.
    Sadece frontend/backend tarafında beklenen JSON yapısını korur.
    """

    prediction = context.get("prediction", {})
    reference = context.get("reference", {})
    absolute_errors = context.get("absolute_errors", {})
    quality_control = context.get("quality_control", {})

    answer = payload.get("answer")
    if not answer:
        answer = (
            "Bu hasta için yapılandırılmış klinik veriler alınmıştır; "
            "ancak LLM yanıtı beklenen formatta üretilememiştir."
        )

    answer_type = payload.get("answer_type", "general_answer")
    source = payload.get("source", "llm_v1")
    confidence = payload.get("confidence", "medium")

    used_metrics = payload.get("used_metrics")

    if not isinstance(used_metrics, dict) or len(used_metrics) == 0:
        if answer_type == "direct_metric":
            used_metrics = {
                "edv_ml": prediction.get("edv_ml"),
                "esv_ml": prediction.get("esv_ml"),
                "ef_percent": prediction.get("ef_percent"),
            }

        elif answer_type == "error_analysis":
            used_metrics = {
                "edv_error_ml": absolute_errors.get("edv_ml"),
                "esv_error_ml": absolute_errors.get("esv_ml"),
                "ef_error_percentage_points": absolute_errors.get("ef_percent"),
                "error_flag": quality_control.get("error_flag"),
            }

        elif answer_type == "clinical_comparison":
            used_metrics = {
                "edv_ml": prediction.get("edv_ml"),
                "esv_ml": prediction.get("esv_ml"),
                "ef_percent": prediction.get("ef_percent"),
                "indexed_lv_volume": None,
                "bsa": None,
                "sex": None,
                "age": None,
            }

        else:
            used_metrics = {
                "prediction": prediction,
                "reference": reference,
                "absolute_errors": absolute_errors,
                "quality_control": quality_control,
            }

    limitations = payload.get(
        "limitations",
        (
            "Bu yanıt otomatik segmentasyon çıktılarından türetilmiştir "
            "ve uzman klinik değerlendirmesinin yerine geçmez."
        ),
    )

    return {
        "answer": answer,
        "answer_type": answer_type,
        "source": source,
        "confidence": confidence,
        "used_metrics": used_metrics,
        "limitations": limitations,
    }


def _generate_openai_answer(result_data: dict, question: str, model_name: str) -> dict:
    """
    OpenAI tabanlı LLM cevabı üretir.
    Örn: gpt-4o-mini
    """

    context = build_llm_context(result_data)

    if not OPENAI_API_KEY:
        return {
            "answer": (
                "LLM entegrasyonu için OPENAI_API_KEY tanımlı değil. "
                "Backend klasöründeki .env dosyasına API anahtarı eklendikten sonra "
                "bu soru LLM tarafından yanıtlanacaktır."
            ),
            "answer_type": "llm_configuration_error",
            "source": "llm_v1",
            "confidence": "low",
            "used_metrics": {
                "patient_id": context.get("patient_id"),
                "provider": "openai",
                "model": model_name,
            },
            "limitations": (
                "LLM API anahtarı tanımlı olmadığı için gerçek LLM cevabı üretilemedi."
            ),
        }

    client = OpenAI(api_key=OPENAI_API_KEY)

    messages = build_llm_messages(
        result_data=result_data,
        question=question,
    )

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw_text = completion.choices[0].message.content
        payload = _extract_json(raw_text)

        return _normalize_llm_payload(payload, context)

    except Exception as exc:
        return {
            "answer": (
                "LLM çağrısı sırasında bir hata oluştu. "
                "API anahtarı, model adı, internet bağlantısı ve kota durumunu kontrol edin."
            ),
            "answer_type": "llm_runtime_error",
            "source": "llm_v1",
            "confidence": "low",
            "used_metrics": {
                "patient_id": context.get("patient_id"),
                "provider": "openai",
                "model": model_name,
            },
            "limitations": str(exc),
        }


def _qwen_not_configured_response(
    result_data: dict, question: str, model_name: str
) -> dict:
    """
    Qwen3-8B-Instruct seçildiğinde, henüz local/Ollama entegrasyonu yapılmadıysa
    frontend'in 500 almaması için kontrollü cevap döndürür.
    """

    context = build_llm_context(result_data)

    return {
        "answer": (
            "Qwen3-8B-Instruct karşılaştırma modeli seçildi; ancak bu model için local/Ollama "
            "bağlantısı henüz backend'e entegre edilmedi. Şu an çalışan aktif LLM modeli "
            "GPT-4o-mini'dir. Qwen entegrasyonu eklendikten sonra aynı hasta verisi ve aynı "
            "sorularla karşılaştırma yapılabilecektir."
        ),
        "answer_type": "llm_provider_not_configured",
        "source": "llm_v1",
        "confidence": "low",
        "used_metrics": {
            "patient_id": context.get("patient_id"),
            "provider": "qwen",
            "model": model_name,
        },
        "limitations": (
            "Qwen3-8B-Instruct henüz backend tarafında çalıştırılabilir sağlayıcı olarak yapılandırılmamıştır."
        ),
    }


def generate_llm_answer(
    result_data: dict,
    question: str,
    llm_provider: str = None,
    llm_model: str = None,
) -> dict:
    """
    Full LLM VQA cevabı üretir.

    Bu fonksiyon:
    - OpenAI seçilirse GPT-4o-mini gibi OpenAI modelini çağırır.
    - Qwen seçilirse şimdilik kontrollü 'not configured' cevabı döndürür.
    - İleride Qwen/Ollama entegrasyonu bu fonksiyona eklenecektir.
    """

    provider = (llm_provider or DEFAULT_LLM_PROVIDER or "openai").casefold().strip()
    model_name = llm_model or OPENAI_MODEL or DEFAULT_LLM_MODEL

    if provider in ["openai", "gpt", "gpt_api"]:
        return _generate_openai_answer(
            result_data=result_data,
            question=question,
            model_name=model_name,
        )

    if provider in ["qwen", "qwen3", "ollama", "local"]:
        return _qwen_not_configured_response(
            result_data=result_data,
            question=question,
            model_name=model_name,
        )

    context = build_llm_context(result_data)

    return {
        "answer": (
            f"Desteklenmeyen LLM sağlayıcısı seçildi: {provider}. "
            "Lütfen openai veya qwen sağlayıcısını kullanın."
        ),
        "answer_type": "unsupported_llm_provider",
        "source": "llm_v1",
        "confidence": "low",
        "used_metrics": {
            "patient_id": context.get("patient_id"),
            "provider": provider,
            "model": model_name,
        },
        "limitations": "Seçilen LLM sağlayıcısı backend tarafından desteklenmiyor.",
    }
