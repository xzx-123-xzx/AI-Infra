from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import httpx
from pypdf import PdfReader

from common.config import conf
from common.logger import my_logger

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json"}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def parse_file(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    my_logger.info("Parsing file: %s suffix=%s", path.name, suffix)

    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    if suffix in IMAGE_SUFFIXES:
        return _parse_image(path)
    if suffix in AUDIO_SUFFIXES:
        return _parse_audio(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _parse_image(path: Path) -> str:
    backend = conf.OCR_BACKEND
    if backend == "tesseract":
        try:
            import pytesseract
            from PIL import Image

            return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").strip()
        except ImportError as exc:
            raise ValueError("pytesseract/Pillow not installed") from exc
    if backend == "api":
        return _ocr_via_vision_api(path)
    raise ValueError(f"OCR not enabled for image (OCR_BACKEND={backend})")


def _ocr_via_vision_api(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    payload = {
        "model": conf.OCR_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请提取图片中全部文字，保持原始段落结构。"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                ],
            }
        ],
        "max_tokens": 4096,
    }
    base = conf.MODEL_BASE_URL.rstrip("/")
    url = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {conf.MODEL_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _parse_audio(path: Path) -> str:
    if conf.ASR_BACKEND != "api":
        raise ValueError(f"ASR not enabled (ASR_BACKEND={conf.ASR_BACKEND})")
    base = conf.MODEL_BASE_URL.rstrip("/")
    url = f"{base}/audio/transcriptions" if base.endswith("/v1") else f"{base}/v1/audio/transcriptions"
    with httpx.Client(timeout=300.0) as client:
        with path.open("rb") as f:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {conf.MODEL_API_KEY}"},
                files={"file": (path.name, f)},
                data={"model": conf.ASR_MODEL},
            )
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, dict):
        return str(data.get("text", "")).strip()
    return str(data).strip()
