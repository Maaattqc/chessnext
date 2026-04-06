"""
Chess position analysis logic.

Uses Stockfish when available; falls back to a material-count heuristic
so the service can run without a local engine binary.
"""

from __future__ import annotations

import os
from typing import Any

import chess

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

def _stockfish_analysis(fen: str, depth: int) -> dict[str, Any] | None:
    """Try to analyse with Stockfish. Returns ``None`` when unavailable."""
    try:
        import chess.engine  # noqa: F811 — intentional lazy import
    except ImportError:
        return None

    stockfish_path = os.getenv("STOCKFISH_PATH", "")
    if not stockfish_path:
        return None

    try:
        engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    except (FileNotFoundError, OSError, chess.engine.EngineTerminatedError):
        return None

    try:
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(depth=depth))

        score = info.get("score")
        pv = info.get("pv", [])

        # Normalise score to white's perspective (centipawns or mate).
        if score is not None:
            white_score = score.white()
            if white_score.is_mate():
                eval_result = {"type": "mate", "value": white_score.mate()}
            else:
                eval_result = {"type": "cp", "value": white_score.score()}
        else:
            eval_result = {"type": "cp", "value": 0}

        best_move = str(pv[0]) if pv else None
        best_line = [str(m) for m in pv[:5]]

        return {
            "eval": eval_result,
            "bestMove": best_move,
            "bestLine": best_line,
            "depth": depth,
            "source": "stockfish",
        }
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


def _mock_analysis(fen: str, depth: int) -> dict[str, Any]:
    """Return a plausible evaluation based on material balance."""
    board = chess.Board(fen)

    material = 0
    for piece_type, value in PIECE_VALUES.items():
        material += len(board.pieces(piece_type, chess.WHITE)) * value
        material -= len(board.pieces(piece_type, chess.BLACK)) * value

    # Generate a legal move as "best move" so the response is usable.
    legal_moves = list(board.legal_moves)
    best_move = str(legal_moves[0]) if legal_moves else None

    return {
        "eval": {"type": "cp", "value": material},
        "bestMove": best_move,
        "bestLine": [str(m) for m in legal_moves[:3]],
        "depth": depth,
        "source": "mock",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_position(fen: str, depth: int = 20) -> dict[str, Any]:
    """Analyse a chess position and return evaluation data.

    Tries Stockfish first; falls back to a material-count heuristic.
    """
    # Validate before analysis (caller should have validated already, but
    # defence-in-depth is cheap).
    validate_fen(fen)

    result = _stockfish_analysis(fen, depth)
    if result is not None:
        return result

    return _mock_analysis(fen, depth)
