import { Chess } from "chess.js";

/**
 * Convert UCI move (e.g. "g1f3") to SAN (e.g. "Nf3") for display.
 * Returns the UCI string as fallback if conversion fails.
 */
export function uciToSan(fen: string, uci: string): string {
  if (!uci || uci.length < 4) return uci;

  try {
    const game = new Chess(fen);
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const promotion = uci.length > 4 ? uci[4] : undefined;

    const result = game.move({ from, to, promotion });
    return result?.san || uci;
  } catch {
    return uci;
  }
}

/**
 * Convert a list of UCI moves to SAN, playing them sequentially.
 */
export function uciLineToSan(fen: string, uciMoves: string[]): string[] {
  if (!uciMoves.length) return [];

  const game = new Chess(fen);
  const result: string[] = [];

  for (const uci of uciMoves) {
    if (uci.length < 4) {
      result.push(uci);
      continue;
    }
    try {
      const from = uci.slice(0, 2);
      const to = uci.slice(2, 4);
      const promotion = uci.length > 4 ? uci[4] : undefined;
      const move = game.move({ from, to, promotion });
      result.push(move?.san || uci);
    } catch {
      result.push(uci);
      break;
    }
  }

  return result;
}

/**
 * Convert a SAN move (e.g. "Nf3") to from/to squares for arrow display.
 * Returns null if conversion fails.
 */
export function sanToSquares(
  fen: string,
  san: string
): { from: string; to: string } | null {
  if (!san) return null;

  try {
    const game = new Chess(fen);
    const move = game.move(san);
    if (move) {
      return { from: move.from, to: move.to };
    }
  } catch {
    // Maybe it's already UCI
    if (san.length >= 4 && san[0] >= "a" && san[0] <= "h") {
      return { from: san.slice(0, 2), to: san.slice(2, 4) };
    }
  }
  return null;
}
