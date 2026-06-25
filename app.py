#!/usr/bin/env python3
"""Production FastAPI server for Body Composition Analysis (ONNX)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from bodyfat_service import AnalysisResult, BodyFatService

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"
MODEL_PATH = (
    Path(os.environ.get("BODYFAT_MODEL_PATH", "")).expanduser()
    if os.environ.get("BODYFAT_MODEL_PATH")
    else None
)

_service: BodyFatService | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _service
    _service = BodyFatService(MODEL_PATH)
    yield
    _service = None


app = FastAPI(
    title="Body Composition Analysis",
    description="ONNX body-fat API for mukitmoves.com",
    lifespan=lifespan,
)

allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://mukitmoves.com,https://www.mukitmoves.com,http://localhost:8080,http://127.0.0.1:8080",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_service() -> BodyFatService:
    if _service is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return _service


def result_to_dict(r: AnalysisResult) -> dict:
    return {
        "body_fat_pct": r.body_fat_pct,
        "lean_mass_kg": r.lean_mass_kg,
        "fat_mass_kg": r.fat_mass_kg,
        "bmi": r.bmi,
        "category": r.category,
        "category_key": r.category_key,
        "preprocess_front": r.preprocess_front,
        "preprocess_side": r.preprocess_side,
        "front_silhouette_b64": r.front_silhouette_b64,
        "side_silhouette_b64": r.side_silhouette_b64,
    }


@app.get("/health")
async def health():
    svc = get_service()
    return JSONResponse(
        {
            "status": "ok",
            "backend": "onnx",
            "model": str(svc.model_path.name),
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/api/analyze")
async def analyze(
    front_photo: UploadFile = File(...),
    side_photo: UploadFile = File(...),
    weight_kg: float = Form(...),
    height_feet: float = Form(...),
    height_inches: float = Form(...),
    gender: str = Form(...),
):
    if weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be positive")
    if height_feet < 0 or height_inches < 0 or height_inches >= 12:
        raise HTTPException(status_code=400, detail="Invalid height")
    if height_feet == 0 and height_inches == 0:
        raise HTTPException(status_code=400, detail="Height is required")

    front_bytes = await front_photo.read()
    side_bytes = await side_photo.read()
    if not front_bytes or not side_bytes:
        raise HTTPException(status_code=400, detail="Both photos are required")

    svc = get_service()
    height_cm = svc.feet_inches_to_cm(height_feet, height_inches)

    try:
        result = svc.analyze_uploads(
            front_bytes,
            side_bytes,
            weight_kg=weight_kg,
            height_cm=height_cm,
            gender=gender,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return result_to_dict(result)
