# =========================================================
# RESULT LOADER SERVICE
# =========================================================

from pathlib import Path
import json


class ResultNotFoundError(Exception):
    """
    Hasta sonucu, manifest veya summary dosyası bulunamadığında kullanılır.
    FastAPI bağımlılığı yoktur; HTTP hatasına main.py içinde çevrilir.
    """
    pass


class ResultLoader:
    """
    Hasta bazlı JSON sonuçlarını, manifest ve summary dosyalarını okuyan servis.

    Bu katman FastAPI'den bağımsızdır.
    Görevi:
    - manifest.json okumak
    - summary_3d_unet.json okumak
    - patients/patientXXX_result.json okumak
    - hasta ID formatını normalize etmek
    - health için dosya durumunu raporlamak
    """

    def __init__(self, json_data_root: Path):
        self.json_data_root = Path(json_data_root)
        self.patients_dir = self.json_data_root / "patients"
        self.manifest_path = self.json_data_root / "manifest.json"
        self.summary_path = self.json_data_root / "summary_3d_unet.json"

    @staticmethod
    def normalize_patient_id(patient_id: str) -> str:
        """
        Farklı hasta ID girişlerini standart patientXXX formatına çevirir.

        Örnek:
        - patient1   -> patient001
        - patient01  -> patient001
        - PATIENT100 -> patient100
        - patient100 -> patient100
        """

        if patient_id is None:
            return ""

        pid = str(patient_id).strip().lower()

        if pid.startswith("patient"):
            number_part = pid.replace("patient", "", 1)

            if number_part.isdigit():
                return f"patient{int(number_part):03d}"

        return pid

    @staticmethod
    def _load_json_file(path: Path):
        """
        Verilen JSON dosyasını okur.
        Dosya yoksa ResultNotFoundError fırlatır.
        """

        if not path.exists():
            raise ResultNotFoundError(f"JSON file not found: {path}")

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def load_manifest(self):
        """
        manifest.json dosyasını okur.
        """

        return self._load_json_file(self.manifest_path)

    def load_summary(self):
        """
        summary_3d_unet.json dosyasını okur.
        """

        return self._load_json_file(self.summary_path)

    def load_patient_result(self, patient_id: str):
        """
        Belirli bir hastanın hasta bazlı JSON sonucunu okur.

        Örnek:
        patient100 -> patients/patient100_result.json
        """

        normalized_patient_id = self.normalize_patient_id(patient_id)
        result_path = self.patients_dir / f"{normalized_patient_id}_result.json"

        if not result_path.exists():
            raise ResultNotFoundError(
                f"No result file found for patient_id: {normalized_patient_id}"
            )

        return self._load_json_file(result_path)

    def list_patients(self):
        """
        manifest.json içinden hasta listesini döndürür.
        """

        manifest = self.load_manifest()
        patients = manifest.get("patients", [])

        return {
            "count": len(patients),
            "patients": patients
        }

    def health_status(self):
        """
        Backend'in JSON veri klasörünü doğru okuyup okuyamadığını kontrol eder.
        """

        patient_count = 0

        if self.patients_dir.exists():
            patient_count = len(list(self.patients_dir.glob("*_result.json")))

        return {
            "json_data_root": str(self.json_data_root),
            "manifest_exists": self.manifest_path.exists(),
            "summary_exists": self.summary_path.exists(),
            "patients_dir_exists": self.patients_dir.exists(),
            "patient_count": patient_count
        }