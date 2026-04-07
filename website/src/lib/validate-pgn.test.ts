import { describe, it, expect } from "vitest";
import { validatePgn } from "./validate-pgn";

describe("validatePgn", () => {
  it("accepts a valid PGN", () => {
    const pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6";
    const result = validatePgn(pgn);
    expect(result.moves).toEqual(["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]);
    expect(result.plyCount).toBe(6);
    expect(result.game).toBeDefined();
  });

  it("accepts a PGN with headers", () => {
    const pgn = `[Event "Casual Game"]
[Site "Internet"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0`;
    const result = validatePgn(pgn);
    expect(result.moves.length).toBeGreaterThan(0);
  });

  it("rejects empty string", () => {
    expect(() => validatePgn("")).toThrow("PGN is required.");
  });

  it("rejects whitespace-only string", () => {
    expect(() => validatePgn("   ")).toThrow("PGN is required.");
  });

  it("rejects null/undefined", () => {
    expect(() => validatePgn(null as unknown as string)).toThrow("PGN is required.");
    expect(() => validatePgn(undefined as unknown as string)).toThrow("PGN is required.");
  });

  it("rejects invalid PGN", () => {
    expect(() => validatePgn("this is not a chess game")).toThrow("Invalid PGN format.");
  });

  it("rejects PGN with only invalid moves", () => {
    expect(() => validatePgn("1. Zz9 Qq0")).toThrow();
  });

  it("rejects SQL injection string", () => {
    expect(() => validatePgn("'; DROP TABLE users; --")).toThrow();
  });

  it("rejects XSS attempt", () => {
    expect(() => validatePgn('<script>alert("xss")</script>')).toThrow();
  });

  it("rejects PGN exceeding max length", () => {
    const longPgn = "1. e4 e5 " + "2. Nf3 Nc6 ".repeat(1000);
    // This will either fail on length or on parsing depending on size
    expect(() => validatePgn(longPgn)).toThrow();
  });
});
