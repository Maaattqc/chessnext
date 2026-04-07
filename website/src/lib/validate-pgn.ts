import { Chess } from "chess.js";

const MAX_PGN_LENGTH = 10_000;
const MAX_MOVES = 500;

export interface ValidatedGame {
  /** The chess.js instance with the loaded game */
  game: Chess;
  /** The full move history */
  moves: string[];
  /** Total number of half-moves (plies) */
  plyCount: number;
}

export function validatePgn(pgn: string): ValidatedGame {
  if (!pgn || typeof pgn !== "string") {
    throw new Error("PGN is required.");
  }

  const trimmed = pgn.trim();

  if (trimmed.length === 0) {
    throw new Error("PGN is required.");
  }

  if (trimmed.length > MAX_PGN_LENGTH) {
    throw new Error(`PGN too long (max ${MAX_PGN_LENGTH} characters).`);
  }

  const game = new Chess();

  try {
    game.loadPgn(trimmed);
  } catch {
    throw new Error("Invalid PGN format.");
  }

  const moves = game.history();

  if (moves.length === 0) {
    throw new Error("PGN contains no moves.");
  }

  if (moves.length > MAX_MOVES) {
    throw new Error(`Too many moves (max ${MAX_MOVES}).`);
  }

  return {
    game,
    moves,
    plyCount: moves.length,
  };
}
