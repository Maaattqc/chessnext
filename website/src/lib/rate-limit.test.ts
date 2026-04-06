import { describe, it, expect } from "vitest";
import { rateLimit } from "./rate-limit";

describe("rateLimit", () => {
  it("returns success when limiter is null (dev mode)", async () => {
    const result = await rateLimit(null, "test-id");
    expect(result.success).toBe(true);
  });
});
