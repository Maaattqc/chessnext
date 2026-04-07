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
 * Returns as many SAN moves as possible; falls back to UCI for failures.
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
      break; // Can't continue after a failed move
    }
  }

  return result;
}
