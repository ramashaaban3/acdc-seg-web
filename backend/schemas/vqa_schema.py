from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class VQARequest(BaseModel):
    """
    Frontend'den /vqa/ask endpoint'ine gelen istek gövdesi.

    Varsayılan seçim:
    - segmentation_model: 3D U-Net
    - llm_provider: OpenAI
    - llm_model: GPT-4o-mini
    """

    patient_id: str = Field(
        ..., example="patient100", description="Hasta kimliği. Örnek: patient100"
    )

    question: str = Field(
        ...,
        example="Bu hastanın EF değeri kaç?",
        description="Kullanıcının VQA sistemine sorduğu klinik soru.",
    )

    mode: Optional[Literal["llm", "auto", "rules"]] = Field(
        default="auto",
        example="auto",
        description="API uyumluluğu için korunmuştur. Full LLM akışında sistem LLM modunda çalışır.",
    )

    segmentation_model: Optional[Literal["3d_unet", "2d_resunet", "3d_resunet"]] = (
        Field(
            default="3d_unet",
            example="3d_unet",
            description="Klinik metriklerin hangi segmentasyon modeli çıktısından okunacağını belirler.",
        )
    )

    llm_provider: Optional[str] = Field(
        default="openai",
        example="openai",
        description="LLM sağlayıcısı. Örnek: openai veya qwen.",
    )

    llm_model: Optional[str] = Field(
        default="gpt-4o-mini",
        example="gpt-4o-mini",
        description="Kullanılacak LLM modeli. Örnek: gpt-4o-mini veya qwen3-8b-instruct.",
    )


class VQAResponse(BaseModel):
    """
    /vqa/ask endpoint'inden frontend'e dönen cevap.

    response.answer:
    - Kullanıcıya gösterilecek doğal dil LLM cevabıdır.

    clinical_metrics / quality_control / ui:
    - Frontend kartları, hata bilgileri ve overlay alanları için kullanılır.
    """

    patient_id: str
    question: str

    vqa_version: str
    mode: str
    question_type: str

    response: Dict[str, Any]

    segmentation_model: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None

    clinical_metrics: Optional[Dict[str, Any]] = None
    quality_control: Optional[Dict[str, Any]] = None
    phase_info: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    ui: Optional[Dict[str, Any]] = None
