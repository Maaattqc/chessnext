import { describe, it, expect } from "vitest";
import { validateFen } from "./validate-fen";

describe("validateFen", () => {
  it("accepts valid starting position", () => {
    const result = validateFen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    expect(result.valid).toBe(true);
  });

  it("accepts valid position after 1.e4", () => {
    const result = validateFen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1");
    expect(result.valid).toBe(true);
  });

  it("rejects empty string", () => {
    const result = validateFen("");
    expect(result.valid).toBe(false);
    expect(result.error).toBe("FEN is required.");
  });

  it("rejects null/undefined", () => {
    const result = validateFen(null as unknown as string);
    expect(result.valid).toBe(false);
  });

  it("rejects FEN longer than 100 characters", () => {
    const longFen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" + "x".repeat(50);
    const result = validateFen(longFen);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("too long");
  });

  it("rejects FEN with invalid format", () => {
    const result = validateFen("not a valid fen string");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("Invalid FEN format");
  });

  it("rejects SQL injection attempt", () => {
    const result = validateFen("'; DROP TABLE users; --");
    expect(result.valid).toBe(false);
  });

  it("rejects XSS attempt", () => {
    const result = validateFen('<script>alert("xss")</script>');
    expect(result.valid).toBe(false);
  });

  it("rejects FEN with too many kings", () => {
    const result = validateFen("rnbqKbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKKBNR w KQkq - 0 1");
    expect(result.valid).toBe(false);
  });
});
