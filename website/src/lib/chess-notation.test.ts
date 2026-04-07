import { describe, it, expect } from "vitest";
import { uciToSan, uciLineToSan } from "./chess-notation";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

describe("uciToSan", () => {
  it("converts e2e4 to e4", () => {
    expect(uciToSan(STARTING_FEN, "e2e4")).toBe("e4");
  });

  it("converts g1f3 to Nf3", () => {
    expect(uciToSan(STARTING_FEN, "g1f3")).toBe("Nf3");
  });

  it("converts b1c3 to Nc3", () => {
    expect(uciToSan(STARTING_FEN, "b1c3")).toBe("Nc3");
  });

  it("converts d2d4 to d4", () => {
    expect(uciToSan(STARTING_FEN, "d2d4")).toBe("d4");
  });

  it("returns UCI as fallback for invalid move", () => {
    expect(uciToSan(STARTING_FEN, "a1a8")).toBe("a1a8");
  });

  it("returns empty string for empty input", () => {
    expect(uciToSan(STARTING_FEN, "")).toBe("");
  });

  it("handles promotion", () => {
    const promoFen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1";
    const san = uciToSan(promoFen, "a7a8q");
    expect(san.startsWith("a8=Q")).toBe(true); // May include + or # for check
  });
});

describe("uciLineToSan", () => {
  it("converts a line of moves", () => {
    const line = ["e2e4", "e7e5", "g1f3"];
    const san = uciLineToSan(STARTING_FEN, line);
    expect(san).toEqual(["e4", "e5", "Nf3"]);
  });

  it("returns empty array for empty input", () => {
    expect(uciLineToSan(STARTING_FEN, [])).toEqual([]);
  });
});
