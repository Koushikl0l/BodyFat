"""Shared preprocessing and ONNX helpers for production deployment."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
META_DIM = 4


def encode_gender(gender: str) -> float:
    return 1.0 if gender.strip().lower() == "male" else 0.0


def default_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.Grayscale(num_output_channels=3),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def build_meta_array(height_cm: float, weight_kg: float, gender: str) -> np.ndarray:
    height_m = height_cm / 100.0
    bmi = weight_kg / max(height_m * height_m, 1e-6)
    return np.array(
        [[height_cm / 200.0, weight_kg / 150.0, encode_gender(gender), bmi / 40.0]],
        dtype=np.float32,
    )


def tensor_from_pil(image: Image.Image, transform: transforms.Compose | None = None) -> torch.Tensor:
    transform = transform or default_transform()
    return transform(image.convert("RGB"))


def default_onnx_path(deploy_dir: Path) -> Path:
    local = deploy_dir / "models" / "bodyfat_student.onnx"
    if local.exists():
        return local
    repo = deploy_dir.parent / "outputs" / "bodyfat_student.onnx"
    if repo.exists():
        return repo
    raise FileNotFoundError(
        f"ONNX model not found. Copy outputs/bodyfat_student.onnx to {local}"
    )


def load_onnx_session(onnx_path: Path):
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError("ONNX inference requires: pip install onnxruntime") from exc

    providers = ["CPUExecutionProvider"]
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        providers.insert(0, "CUDAExecutionProvider")
    return ort.InferenceSession(str(onnx_path), providers=providers)
