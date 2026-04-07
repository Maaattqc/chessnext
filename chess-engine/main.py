"""
ChessNext Analysis Engine — FastAPI service.

Provides chess position evaluation and coaching narratives.
Designed to run as an internal micro-service behind the main website backend.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from analysis import analyze_position, validate_fen
from coach import generate_narrative, generate_human_move

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

INTERNAL_KEY = os.getenv("CHESS_ENGINE_INTERNAL_KEY", "")

app = FastAPI(
    title="ChessNext Analysis Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://chessnext.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate limiting (placeholder)
# ---------------------------------------------------------------------------
# TODO: integrate a proper rate-limiter such as slowapi or a Redis
# token-bucket.  For now every request is allowed through.
# Suggested limits:
#   - /internal/analyze: 60 requests/min per caller
#   - /health: no limit


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    fen: str = Field(..., max_length=100, description="FEN string of the position.")
    userRating: int = Field(..., ge=0, le=4000, description="Player rating (0-4000).")
    depth: int = Field(default=20, ge=1, le=40, description="Search depth (1-40).")


class EvalResult(BaseModel):
    type: str = Field(..., description="'cp' for centipawns or 'mate'.")
    value: int = Field(..., description="Centipawn score or moves-to-mate.")


class AnalyzeResponse(BaseModel):
    evaluation: dict[str, Any] = Field(
        ..., description="Engine evaluation (eval, bestMove, bestLine, depth, source)."
    )
    concepts: list[str] = Field(
        default_factory=list,
        description="Positional/tactical concepts identified.",
    )
    coachNarrative: str = Field(
        ..., description="Human-readable coaching paragraph."
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    status: int


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Exception handler — normalise all errors to the API spec format
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _status_to_code(exc.status_code),
                "message": str(exc.detail),
                "status": exc.status_code,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "status": 500,
            }
        },
    )


def _status_to_code(status: int) -> str:
    mapping: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }
    return mapping.get(status, "UNKNOWN_ERROR")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}


@app.post("/internal/analyze", response_model=AnalyzeResponse)
async def internal_analyze(
    body: AnalyzeRequest,
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
) -> AnalyzeResponse:
    """Analyse a chess position and return evaluation + coaching narrative.

    Requires a valid ``X-Internal-Key`` header.
    """

    # --- Auth -----------------------------------------------------------
    if not INTERNAL_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: CHESS_ENGINE_INTERNAL_KEY is not set.",
        )
    if x_internal_key != INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal key.")

    # --- FEN validation -------------------------------------------------
    try:
        validate_fen(body.fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # --- Analysis -------------------------------------------------------
    evaluation = analyze_position(body.fen, body.depth)

    # --- Concepts (placeholder — will be enriched later) ----------------
    concepts: list[str] = _detect_concepts(body.fen)

    # --- Coach narrative ------------------------------------------------
    narrative = generate_narrative(
        fen=body.fen,
        evaluation=evaluation,
        user_rating=body.userRating,
        concepts=concepts,
    )

    return AnalyzeResponse(
        evaluation=evaluation,
        concepts=concepts,
        coachNarrative=narrative,
    )


class HumanMoveRequest(BaseModel):
    fen: str = Field(..., max_length=100)
    userRating: int = Field(..., ge=0, le=4000)
    engineBestMove: str = Field(..., max_length=10)
    engineTopMoves: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/internal/human-move")
async def internal_human_move(
    body: HumanMoveRequest,
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
) -> dict[str, Any]:
    """Return the best move adjusted for the player's rating level."""

    if not INTERNAL_KEY or x_internal_key != INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal key.")

    try:
        validate_fen(body.fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = generate_human_move(
        fen=body.fen,
        evaluation={"bestMove": body.engineBestMove},
        user_rating=body.userRating,
        top_moves=body.engineTopMoves,
    )
    return result


# ---------------------------------------------------------------------------
# Concept detection (lightweight, rule-based placeholder)
# ---------------------------------------------------------------------------

def _detect_concepts(fen: str) -> list[str]:
    """Return a list of high-level positional/tactical tags.

    This is intentionally simplistic — a future version will use pattern
    matching or a neural classifier.
    """
    import chess as _chess

    board = _chess.Board(fen)
    concepts: list[str] = []

    # Check for checks.
    if board.is_check():
        concepts.append("check")

    # Simple material imbalance flag.
    white_material = sum(
        len(board.pieces(pt, _chess.WHITE)) * v
        for pt, v in [
            (_chess.PAWN, 1),
            (_chess.KNIGHT, 3),
            (_chess.BISHOP, 3),
            (_chess.ROOK, 5),
            (_chess.QUEEN, 9),
        ]
    )
    black_material = sum(
        len(board.pieces(pt, _chess.BLACK)) * v
        for pt, v in [
            (_chess.PAWN, 1),
            (_chess.KNIGHT, 3),
            (_chess.BISHOP, 3),
            (_chess.ROOK, 5),
            (_chess.QUEEN, 9),
        ]
    )
    if abs(white_material - black_material) >= 3:
        concepts.append("material_imbalance")

    # Castling rights still available?
    if board.has_castling_rights(_chess.WHITE) or board.has_castling_rights(_chess.BLACK):
        concepts.append("castling_available")

    # En-passant possible?
    if board.has_legal_en_passant():
        concepts.append("en_passant")

    return concepts


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
