import pytest

from src.main import app
from src.middleware.auth import authenticate


def _fake_generate_pdf(content, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"%PDF-1.4\n% mock pdf\n")
    return output_path


@pytest.mark.asyncio
async def test_export_pdf_success(async_client, monkeypatch):
    from src.routes import documents

    app.dependency_overrides[authenticate] = lambda: {"id": "test-user"}
    monkeypatch.setattr(documents, "_generate_pdf", _fake_generate_pdf)

    try:
        response = await async_client.post(
            "/api/documents/export-pdf",
            json={"content": "# Test document", "filename": "my-draft"},
        )
    finally:
        app.dependency_overrides.pop(authenticate, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert b"%PDF-1.4" in response.content


@pytest.mark.asyncio
async def test_export_pdf_rejects_empty_content(async_client):
    app.dependency_overrides[authenticate] = lambda: {"id": "test-user"}

    try:
        response = await async_client.post(
            "/api/documents/export-pdf",
            json={"content": "   ", "filename": "empty.pdf"},
        )
    finally:
        app.dependency_overrides.pop(authenticate, None)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_export_pdf_requires_auth(async_client):
    response = await async_client.post(
        "/api/documents/export-pdf",
        json={"content": "hello world"},
    )

    assert response.status_code == 400
