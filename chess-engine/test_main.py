"""Tests for the FastAPI application."""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("CHESS_ENGINE_INTERNAL_KEY", "test-key-123")

from main import app

client = TestClient(app)


class TestHealthCheck:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestInternalAnalyze:
    def test_rejects_missing_auth(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "userRating": 1500, "depth": 10},
        )
        # FastAPI may return 422 (missing header) or 401/403 (unauthorized)
        assert response.status_code in (401, 403, 422)

    def test_rejects_wrong_key(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "userRating": 1500, "depth": 10},
            headers={"X-Internal-Key": "wrong-key"},
        )
        assert response.status_code in (401, 403)

    def test_accepts_valid_request(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "userRating": 1500, "depth": 10},
            headers={"X-Internal-Key": "test-key-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert "coachNarrative" in data

    def test_rejects_invalid_fen(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "not-a-fen", "userRating": 1500, "depth": 10},
            headers={"X-Internal-Key": "test-key-123"},
        )
        assert response.status_code == 400

    def test_rejects_sql_injection_fen(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "'; DROP TABLE users; --", "userRating": 1500, "depth": 10},
            headers={"X-Internal-Key": "test-key-123"},
        )
        assert response.status_code == 400

    def test_rejects_too_long_fen(self):
        response = client.post(
            "/internal/analyze",
            json={"fen": "a" * 200, "userRating": 1500, "depth": 10},
            headers={"X-Internal-Key": "test-key-123"},
        )
        # May be 400 (our validation) or 422 (pydantic)
        assert response.status_code in (400, 422)
