"""
Chess position analysis logic.

Uses Stockfish when available; falls back to a material-count heuristic
so the service can run without a local engine binary.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import chess
import chess.engine

# ---------------------------------------------------------------------------
# Stockfish path resolution
# ---------------------------------------------------------------------------

# 1. Honour the STOCKFISH_PATH env var if set.
# 2. Otherwise fall back to ./bin/stockfish.exe next to this file.
_DEFAULT_STOCKFISH = str(
    pathlib.Path(__file__).resolve().parent / "bin" / "stockfish.exe"
)
STOCKFISH_PATH: str = os.getenv("STOCKFISH_PATH", _DEFAULT_STOCKFISH)

# ---------------------------------------------------------------------------
# FEN validation
# ---------------------------------------------------------------------------

MAX_FEN_LENGTH = 100


def validate_fen(fen: str) -> chess.Board:
    """Parse and validate a FEN string.

    Returns a ``chess.Board`` on success.
    Raises ``ValueError`` with a human-readable message on failure.
    """
    if not fen or not isinstance(fen, str):
        raise ValueError("FEN string is required.")
    if len(fen) > MAX_FEN_LENGTH:
        raise ValueError(f"FEN must be at most {MAX_FEN_LENGTH} characters.")

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ValueError(f"Invalid FEN: {exc}") from exc

    if not board.is_valid():
        raise ValueError("FEN describes an illegal position.")

    return board


# ---------------------------------------------------------------------------
# Stockfish wrapper (best-effort)
# ---------------------------------------------------------------------------

_ANALYSIS_TIMEOUT = 10  # seconds – hard cap per analysis call


def _stockfish_analysis(fen: str, depth: int, multi_pv: int = 1) -> dict[str, Any] | None:
    """Try to analyse with Stockfish. Returns ``None`` when unavailable."""

    if not STOCKFISH_PATH or not os.path.isfile(STOCKFISH_PATH):
        return None

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except (FileNotFoundError, OSError, chess.engine.EngineTerminatedError):
        return None

    try:
        board = chess.Board(fen)
        infos = engine.analyse(
            board,
            chess.engine.Limit(depth=depth, time=_ANALYSIS_TIMEOUT),
            multipv=multi_pv,
        )

        # engine.analyse returns a list when multipv > 1, single dict when 1
        if not isinstance(infos, list):
            infos = [infos]

        lines: list[dict[str, Any]] = []
        for info in infos:
            score = info.get("score")
            pv = info.get("pv", [])

            if score is not None:
                white_score = score.white()
                if white_score.is_mate():
                    eval_result = {"type": "mate", "value": white_score.mate()}
                else:
                    eval_result = {"type": "cp", "value": white_score.score()}
            else:
                eval_result = {"type": "cp", "value": 0}

            lines.append({
                "eval": eval_result,
                "bestMove": str(pv[0]) if pv else None,
                "bestLine": [str(m) for m in pv],
            })

        top = lines[0] if lines else {"eval": {"type": "cp", "value": 0}, "bestMove": None, "bestLine": []}

        return {
            "eval": top["eval"],
            "bestMove": top["bestMove"],
            "bestLine": top["bestLine"],
            "lines": lines,
            "depth": infos[0].get("depth", depth) if infos else depth,
            "source": "stockfish",
        }
    except chess.engine.EngineTerminatedError:
        return None
    finally:
        engine.quit()


# ---------------------------------------------------------------------------
# Material-count mock evaluation
# ---------------------------------------------------------------------------

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}


def _mock_analysis(fen: str, depth: int, multi_pv: int = 1) -> dict[str, Any]:
    """Return a plausible evaluation based on material balance."""
    board = chess.Board(fen)

    material = 0
    for piece_type, value in PIECE_VALUES.items():
        material += len(board.pieces(piece_type, chess.WHITE)) * value
        material -= len(board.pieces(piece_type, chess.BLACK)) * value

    legal_moves = list(board.legal_moves)
    lines: list[dict[str, Any]] = []
    for i in range(min(multi_pv, len(legal_moves))):
        lines.append({
            "eval": {"type": "cp", "value": material},
            "bestMove": str(legal_moves[i]),
            "bestLine": [str(legal_moves[i])],
        })

    if not lines:
        lines.append({"eval": {"type": "cp", "value": material}, "bestMove": None, "bestLine": []})

    return {
        "eval": {"type": "cp", "value": material},
        "bestMove": str(legal_moves[0]) if legal_moves else None,
        "bestLine": [str(m) for m in legal_moves[:3]],
        "lines": lines,
        "depth": depth,
        "source": "mock",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_position(fen: str, depth: int = 20, multi_pv: int = 1) -> dict[str, Any]:
    """Analyse a chess position and return evaluation data.

    Tries Stockfish first; falls back to a material-count heuristic.
    """
    # Validate before analysis (caller should have validated already, but
    # defence-in-depth is cheap).
    validate_fen(fen)

    result = _stockfish_analysis(fen, depth, multi_pv)
    if result is not None:
        return result

    return _mock_analysis(fen, depth, multi_pv)
