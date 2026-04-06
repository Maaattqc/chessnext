import { Chess } from "chess.js";

const FEN_REGEX = /^[rnbqkpRNBQKP1-8/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
const MAX_FEN_LENGTH = 100;

export function validateFen(fen: string): { valid: boolean; error?: string } {
  if (!fen || typeof fen !== "string") {
    return { valid: false, error: "FEN is required." };
  }

  const trimmed = fen.trim();

  if (trimmed.length > MAX_FEN_LENGTH) {
    return { valid: false, error: "FEN too long (max 100 characters)." };
  }

  if (!FEN_REGEX.test(trimmed)) {
    return { valid: false, error: "Invalid FEN format." };
  }

  try {
    new Chess(trimmed);
    return { valid: true };
  } catch {
    return { valid: false, error: "Illegal chess position." };
  }
}
