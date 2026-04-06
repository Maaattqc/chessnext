"""Tests for FEN validation and position analysis."""

import pytest
from analysis import validate_fen, analyze_position


class TestValidateFen:
    def test_valid_starting_position(self):
        board = validate_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert board is not None

    def test_valid_sicilian(self):
        board = validate_fen("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2")
        assert board is not None

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="required"):
            validate_fen("")

    def test_rejects_too_long(self):
        long_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" + "x" * 50
        with pytest.raises(ValueError, match="100"):
            validate_fen(long_fen)

    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            validate_fen("not a fen string")

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError):
            validate_fen("'; DROP TABLE users; --")

    def test_rejects_xss(self):
        with pytest.raises(ValueError):
            validate_fen('<script>alert("xss")</script>')

    def test_rejects_shell_injection(self):
        with pytest.raises(ValueError):
            validate_fen("$(rm -rf /)")

    def test_rejects_none(self):
        with pytest.raises((ValueError, TypeError)):
            validate_fen(None)


class TestAnalyzePosition:
    def test_returns_eval_for_starting_position(self):
        result = analyze_position(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            depth=1,
        )
        assert "eval" in result or "score" in result
        assert "bestMove" in result

    def test_returns_best_move_as_string(self):
        result = analyze_position(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            depth=1,
        )
        assert isinstance(result["bestMove"], str)
        assert len(result["bestMove"]) >= 4  # UCI format: e.g. "e7e5"
