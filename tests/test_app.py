"""
Tests for the Flask web API (app.py).

Uses Flask's test client so no real server process or network call is
needed. LLM-backed endpoints (/api/summarize, /api/ask) are not exercised
here since they require a live provider — see tests/test_document_processor.py
for coverage of the retrieval/chunking logic they depend on.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config  # noqa: E402


@pytest.fixture()
def client(sandbox, sample_txt, sample_docx, sample_xlsx):
    import app as flask_app_module

    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "llm_provider" in data
    assert "base_dir" in data


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"File Assistant" in resp.data


def test_list_files_endpoint(client):
    resp = client.get("/api/files")
    assert resp.status_code == 200
    names = {f["name"] for f in resp.get_json()["files"]}
    assert {"notes.txt", "report.docx", "data.xlsx"} <= names


def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["supported_files"] == 3
    assert data["total_size_bytes"] > 0


def test_read_endpoint(client):
    resp = client.get("/api/read?path=notes.txt")
    assert resp.status_code == 200
    assert "Project Phoenix" in resp.get_json()["text"]


def test_read_endpoint_missing_file(client):
    resp = client.get("/api/read?path=nope.txt")
    assert resp.status_code == 404


def test_read_endpoint_path_traversal_blocked(client):
    resp = client.get("/api/read?path=../../etc/passwd")
    assert resp.status_code == 404
    assert "Access denied" in resp.get_json()["error"]


def test_search_endpoint(client):
    resp = client.get("/api/search?keyword=budget")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["files_matched"] >= 1


def test_search_endpoint_empty_keyword(client):
    resp = client.get("/api/search?keyword=")
    assert resp.status_code == 400


def test_upload_endpoint_accepts_supported_type(client):
    data = {"file": (io.BytesIO(b"hello world"), "new_upload.txt")}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert (config.BASE_DIR / "new_upload.txt").exists()


def test_upload_endpoint_rejects_unsupported_type(client):
    data = {"file": (io.BytesIO(b"fake image bytes"), "image.png")}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.get_json()["error"]


def test_summarize_endpoint_missing_path(client):
    resp = client.post("/api/summarize", json={})
    assert resp.status_code == 400


def test_ask_endpoint_missing_fields(client):
    resp = client.post("/api/ask", json={"path": "notes.txt"})
    assert resp.status_code == 400
