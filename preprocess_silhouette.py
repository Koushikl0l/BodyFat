"""Silhouette preprocessing for body-fat ONNX inference."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

_REMBG_SESSION = None


def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        from rembg import new_session

        _REMBG_SESSION = new_session("u2net")
    return _REMBG_SESSION


def _remove_background(image: Image.Image) -> Image.Image:
    from rembg import remove

    result = remove(image, session=_get_rembg_session())
    if isinstance(result, bytes):
        return Image.open(BytesIO(result)).convert("RGBA")
    return result.convert("RGBA")


def _rgba_to_silhouette(rgba: Image.Image) -> Image.Image:
    alpha = np.array(rgba.split()[-1])
    mask = (alpha > 32).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask, mode="L")

    bbox = mask_img.getbbox()
    if not bbox:
        raise ValueError(
            "Could not detect a person in the photo. Use a full-body photo with a clear background."
        )

    crop_mask = mask_img.crop(bbox)
    width, height = crop_mask.size
    silhouette = Image.new("RGB", (width, height), (255, 255, 255))
    black = Image.new("RGB", (width, height), (0, 0, 0))
    silhouette.paste(black, mask=crop_mask)

    size = max(width, height)
    return ImageOps.pad(silhouette, (size, size), color=(255, 255, 255), centering=(0.5, 0.5))


def prepare_input_image(path: Path | str) -> tuple[Image.Image, str]:
    image_path = Path(path)
    image = Image.open(image_path).convert("RGB")
    rgba = _remove_background(image)
    return _rgba_to_silhouette(rgba), "rembg"


def save_silhouette(image: Image.Image, path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
