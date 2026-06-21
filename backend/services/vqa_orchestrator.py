# =========================================================
# VQA ORCHESTRATOR - FULL LLM VERSION
# =========================================================

from services.llm_vqa_engine import generate_llm_answer


def answer_question(
    result_data: dict,
    question: str,
    mode: str = "llm",
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o-mini",
):
    """
    Full LLM VQA akışı.

    Bu versiyonda:
    - Tüm sorular LLM katmanına yönlendirilir.
    - Rule-based cevap üretimi yapılmaz.
    - question_classifier kullanılmaz.
    - llm_provider ve llm_model frontend'den gelebilir.
    """

    answer = generate_llm_answer(
        result_data=result_data,
        question=question,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

    return {
        "vqa_version": "llm_v1",
        "mode_used": "llm",
        "question_type": answer.get("answer_type", "general_answer"),
        "response": answer,
    }
