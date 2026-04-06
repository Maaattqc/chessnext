import { describe, it, expect } from "vitest";
import { PLANS } from "./stripe";

describe("PLANS", () => {
  it("has exactly 3 paid plans", () => {
    expect(Object.keys(PLANS)).toEqual(["plus", "pro", "coach"]);
  });

  it("plus costs $12", () => {
    expect(PLANS.plus.price).toBe(12);
  });

  it("pro costs $30", () => {
    expect(PLANS.pro.price).toBe(30);
  });

  it("coach costs $60", () => {
    expect(PLANS.coach.price).toBe(60);
  });

  it("all plans have name and priceId fields", () => {
    for (const key of Object.keys(PLANS) as (keyof typeof PLANS)[]) {
      expect(PLANS[key]).toHaveProperty("name");
      expect(PLANS[key]).toHaveProperty("priceId");
      expect(PLANS[key]).toHaveProperty("price");
    }
  });
});
