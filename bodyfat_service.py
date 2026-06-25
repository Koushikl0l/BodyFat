"""ONNX body-fat inference service for production deployment."""

from __future__ import annotations

import base64
import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from inference_utils import (
    build_meta_array,
    default_onnx_path,
    default_transform,
    load_onnx_session,
    tensor_from_pil,
)
from preprocess_silhouette import prepare_input_image, save_silhouette

ROOT = Path(__file__).resolve().parent


@dataclass
class AnalysisResult:
    body_fat_pct: float
    lean_mass_kg: float
    fat_mass_kg: float
    bmi: float
    category: str
    category_key: str
    preprocess_front: str
    preprocess_side: str
    front_silhouette_b64: str
    side_silhouette_b64: str


class BodyFatService:
    def __init__(self, model_path: Path | None = None) -> None:
        onnx_path = model_path or default_onnx_path(ROOT)
        self.model_path = onnx_path
        self.session = load_onnx_session(onnx_path)
        self.transform = default_transform()

    @staticmethod
    def feet_inches_to_cm(feet: float, inches: float) -> float:
        total_in = feet * 12.0 + inches
        return total_in * 2.54

    @staticmethod
    def classify_body_fat(pct: float, gender: str) -> tuple[str, str]:
        g = gender.strip().lower()
        if g == "male":
            if pct <= 5:
                return "Essential fat", "essential"
            if pct <= 13:
                return "Athletes", "athletes"
            if pct <= 17:
                return "Fitness", "fitness"
            if pct <= 24:
                return "Acceptable", "acceptable"
            return "Obese", "obese"
        if pct <= 13:
            return "Essential fat", "essential"
        if pct <= 20:
            return "Athletes", "athletes"
        if pct <= 24:
            return "Fitness", "fitness"
        if pct <= 31:
            return "Acceptable", "acceptable"
        return "Obese", "obese"

    def predict_arrays(
        self,
        front: Image.Image,
        side: Image.Image,
        height_cm: float,
        weight_kg: float,
        gender: str,
    ) -> float:
        front_arr = tensor_from_pil(front, self.transform).unsqueeze(0).numpy()
        side_arr = tensor_from_pil(side, self.transform).unsqueeze(0).numpy()
        meta_arr = build_meta_array(height_cm, weight_kg, gender)
        out = self.session.run(None, {"front": front_arr, "side": side_arr, "meta": meta_arr})[0]
        return float(np.asarray(out).reshape(-1)[0])

    def analyze_uploads(
        self,
        front_bytes: bytes,
        side_bytes: bytes,
        *,
        weight_kg: float,
        height_cm: float,
        gender: str,
    ) -> AnalysisResult:
        gender_norm = gender.strip().lower()
        if gender_norm not in {"male", "female"}:
            raise ValueError("gender must be male or female")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            front_path = tmp_dir / "front_upload.png"
            side_path = tmp_dir / "side_upload.png"
            front_path.write_bytes(front_bytes)
            side_path.write_bytes(side_bytes)

            front_sil, front_mode = prepare_input_image(front_path)
            side_sil, side_mode = prepare_input_image(side_path)

            front_out = tmp_dir / "front_sil.png"
            side_out = tmp_dir / "side_sil.png"
            save_silhouette(front_sil, front_out)
            save_silhouette(side_sil, side_out)

            body_fat_pct = self.predict_arrays(
                front_sil, side_sil, height_cm, weight_kg, gender_norm,
            )

        body_fat_pct = max(3.0, min(60.0, body_fat_pct))
        fat_mass = weight_kg * (body_fat_pct / 100.0)
        lean_mass = weight_kg - fat_mass
        height_m = height_cm / 100.0
        bmi = weight_kg / max(height_m * height_m, 1e-6)
        category, category_key = self.classify_body_fat(body_fat_pct, gender_norm)

        return AnalysisResult(
            body_fat_pct=round(body_fat_pct, 1),
            lean_mass_kg=round(lean_mass, 1),
            fat_mass_kg=round(fat_mass, 1),
            bmi=round(bmi, 1),
            category=category,
            category_key=category_key,
            preprocess_front=front_mode,
            preprocess_side=side_mode,
            front_silhouette_b64=self._pil_to_b64(front_sil),
            side_silhouette_b64=self._pil_to_b64(side_sil),
        )

    @staticmethod
    def _pil_to_b64(image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
