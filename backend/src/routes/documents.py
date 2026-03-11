"""Document export endpoints."""

import importlib.util
import logging
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from ..middleware.auth import authenticate

logger = logging.getLogger(__name__)
router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TOOL_PDF_GENERATOR_PATH = _PROJECT_ROOT / "tool" / "src" / "utils" / "pdf_generator.py"


class ExportPdfRequest(BaseModel):
    content: str = Field(..., description="Document content to export")
    filename: str | None = Field(default=None, description="Optional download filename")

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Content cannot be empty")
        if len(cleaned) > 100_000:
            raise ValueError("Content exceeds max allowed length")
        return cleaned


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return "draft.pdf"

    base = Path(filename).name.strip()
    if not base:
        return "draft.pdf"

    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"

    # Keep filename predictable and safe for Content-Disposition.
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. "
    sanitized = "".join(ch for ch in base if ch in allowed).strip()
    return sanitized or "draft.pdf"


def _generate_pdf(content: str, output_path: Path) -> Path:
    if not _TOOL_PDF_GENERATOR_PATH.exists():
        raise RuntimeError("PDF generator module not found")

    spec = importlib.util.spec_from_file_location("tool_pdf_generator", str(_TOOL_PDF_GENERATOR_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load PDF generator module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    generated = module.generate_pdf_report(content, str(output_path))
    return Path(generated)


def _cleanup_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.warning("Failed to clean up temporary PDF file: %s", path)


@router.post("/documents/export-pdf")
async def export_pdf(
    request: ExportPdfRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(authenticate),
):
    del current_user

    try:
        temp_name = f"draft_{uuid4().hex}.pdf"
        temp_path = Path(tempfile.gettempdir()) / temp_name
        generated_path = _generate_pdf(request.content, temp_path)

        if not generated_path.exists() or generated_path.stat().st_size == 0:
            raise RuntimeError("Generated PDF is empty")

        background_tasks.add_task(_cleanup_file, generated_path)
        download_name = _safe_filename(request.filename)

        return FileResponse(
            path=generated_path,
            media_type="application/pdf",
            filename=download_name,
            headers={"Content-Disposition": f"attachment; filename={download_name}"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to export draft as PDF")
        raise HTTPException(status_code=500, detail="Failed to export PDF") from exc
