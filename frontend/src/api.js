import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE;


function normalizePatients(data) {
  /*
    Backend /patients endpoint'i bazen şu formatta dönebilir:

    {
      count: 100,
      patients: ["patient001", "patient002", ...]
    }

    veya ileride:
    [
      { patient_id: "patient001", real_patient_id: "patient001" }
    ]

    Frontend tarafında tek format kullanmak için normalize ediyoruz.
  */

  if (Array.isArray(data)) {
    return data.map((p) => {
      if (typeof p === "string") {
        return {
          patient_id: p,
          real_patient_id: p,
        };
      }

      return {
        patient_id: p.patient_id || p.real_patient_id,
        real_patient_id: p.real_patient_id || p.patient_id,
      };
    });
  }

  if (Array.isArray(data?.patients)) {
    return data.patients.map((p) => {
      if (typeof p === "string") {
        return {
          patient_id: p,
          real_patient_id: p,
        };
      }

      return {
        patient_id: p.patient_id || p.real_patient_id,
        real_patient_id: p.real_patient_id || p.patient_id,
      };
    });
  }

  return [];
}


export async function getPatients() {
  const r = await axios.get(`${API_BASE}/patients`);
  return normalizePatients(r.data);
}


export async function askVqa({
  patientId,
  question,
  segmentationModel = "3d_unet",
  llmProvider = "openai",
  llmModel = "gpt-4o-mini",
}) {
  const r = await axios.post(`${API_BASE}/vqa/ask`, {
    patient_id: patientId,
    question,
    mode: "auto",

    // Segmentasyon modeli seçimi
    segmentation_model: segmentationModel,

    // LLM modeli seçimi
    llm_provider: llmProvider,
    llm_model: llmModel,
  });

  return r.data;
}