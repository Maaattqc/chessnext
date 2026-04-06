import Stripe from "stripe";

let _stripe: Stripe | null = null;

export function getStripe(): Stripe {
  if (!_stripe) {
    if (!process.env.STRIPE_SECRET_KEY) {
      throw new Error("STRIPE_SECRET_KEY is not set");
    }
    _stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { typescript: true });
  }
  return _stripe;
}

// Re-export as `stripe` for convenience — but lazily initialized
export const stripe = new Proxy({} as Stripe, {
  get(_, prop) {
    return (getStripe() as unknown as Record<string | symbol, unknown>)[prop];
  },
});

export const PLANS = {
  plus: {
    name: "Plus",
    priceId: process.env.STRIPE_PRICE_PLUS || "",
    price: 12,
  },
  pro: {
    name: "Pro",
    priceId: process.env.STRIPE_PRICE_PRO || "",
    price: 30,
  },
  coach: {
    name: "Coach",
    priceId: process.env.STRIPE_PRICE_COACH || "",
    price: 60,
  },
} as const;

export type PlanKey = keyof typeof PLANS;
