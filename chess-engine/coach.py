"""
Claude-powered coaching narrative generator.

Currently returns a template string.  Will be replaced with a real
Anthropic API call once the integration is wired up.
"""

from __future__ import annotations

from typing import Any


def generate_narrative(
    fen: str,
    evaluation: dict[str, Any],
    user_rating: int,
    concepts: list[str],
) -> str:
    """Produce a short coaching narrative for the given position.

    Parameters
    ----------
    fen:
        The FEN of the position being analysed.
    evaluation:
        Output of ``analyze_position`` (eval, bestMove, etc.).
    user_rating:
        The player's current rating — used to calibrate language complexity.
    concepts:
        Strategic/tactical concepts identified in the position.

    Returns
    -------
    str
        A plain-text coaching paragraph.  Eventually this will come from
        Claude; for now it is a deterministic template.
    """
    eval_info = evaluation.get("eval", {})
    eval_type = eval_info.get("type", "cp")
    eval_value = eval_info.get("value", 0)
    best_move = evaluation.get("bestMove", "unknown")
    source = evaluation.get("source", "unknown")

    # Human-readable evaluation summary.
    if eval_type == "mate":
        if eval_value > 0:
            eval_text = f"White has a forced mate in {eval_value}."
        else:
            eval_text = f"Black has a forced mate in {abs(eval_value)}."
    else:
        pawns = eval_value / 100
        if abs(pawns) < 0.3:
            eval_text = "The position is roughly equal."
        elif pawns > 0:
            eval_text = f"White is better by about {pawns:+.1f} pawns."
        else:
            eval_text = f"Black is better by about {abs(pawns):.1f} pawns."

    concepts_text = (
        "Key concepts here: " + ", ".join(concepts) + "."
        if concepts
        else "No specific tactical or strategic themes flagged yet."
    )

    # Adjust tone based on rating band.
    if user_rating < 1000:
        tone = "Let's keep it simple."
    elif user_rating < 1600:
        tone = "Here's something worth thinking about."
    else:
        tone = "At your level, precision matters."

    return (
        f"{tone} {eval_text} "
        f"The engine suggests {best_move} as the strongest continuation. "
        f"{concepts_text} "
        f"(analysis source: {source})"
    )
