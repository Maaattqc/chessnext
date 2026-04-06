import { describe, it, expect } from "vitest";
import { validateFen } from "@/lib/validate-fen";

// We test the validation logic used by the route.
// Full integration tests (with DB + auth) require test DB setup.

describe("analysis position validation", () => {
  it("rejects missing FEN", () => {
    const result = validateFen("");
    expect(result.valid).toBe(false);
  });

  it("accepts valid FEN for analysis", () => {
    const result = validateFen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1");
    expect(result.valid).toBe(true);
  });

  it("rejects FEN with injection attempt", () => {
    const result = validateFen("'; DROP TABLE analyses; --");
    expect(result.valid).toBe(false);
  });
});
