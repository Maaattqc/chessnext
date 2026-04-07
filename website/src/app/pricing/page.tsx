import type { Metadata } from "next";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Check } from "lucide-react";
import { PricingButton } from "./pricing-button";

export const metadata: Metadata = {
  title: "Pricing — ChessNext.ai",
  description: "Start free. Learn superhuman chess concepts from Leela Chess Zero. Upgrade for full access.",
};

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Get started with superhuman concepts",
    features: [
      "3 concepts",
      "1 position analysis / day",
      "Basic AI coach insights",
    ],
    cta: "Start free",
    href: "/login",
    highlight: false,
  },
  {
    name: "Plus",
    price: "$12",
    period: "/ month",
    description: "Full access to all concepts",
    features: [
      "All 50+ concepts",
      "60 analyses / day",
      "5 game analyses / day",
      "Progress tracking",
      "Spaced repetition",
    ],
    cta: "Upgrade to Plus",
    href: "/login",
    highlight: true,
  },
  {
    name: "Pro",
    price: "$30",
    period: "/ month",
    description: "Deep analysis and weakness detection",
    features: [
      "Everything in Plus",
      "Unlimited position analyses",
      "20 game analyses / day",
      "Root-cause analysis",
      "Weakness detection",
      "PGN export",
    ],
    cta: "Upgrade to Pro",
    href: "/login",
    highlight: false,
  },
  {
    name: "Coach",
    price: "$60",
    period: "/ month",
    description: "For coaches and serious competitors",
    features: [
      "Everything in Pro",
      "Unlimited game analyses",
      "Bulk student analysis",
      "Curriculum builder",
      "Priority concept updates",
      "API access",
    ],
    cta: "Upgrade to Coach",
    href: "/login",
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-16">
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold">Simple, transparent pricing</h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Start free. Upgrade when you want more concepts and deeper analysis.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`relative flex flex-col ${
                plan.highlight
                  ? "border-primary shadow-lg shadow-primary/10"
                  : "border-border/40"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-medium text-white">
                  Most popular
                </div>
              )}
              <CardHeader>
                <CardTitle>{plan.name}</CardTitle>
                <div className="mt-2">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-sm text-muted-foreground">
                    {" "}
                    {plan.period}
                  </span>
                </div>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col">
                <ul className="flex-1 space-y-2">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <div className="mt-6">
                  <PricingButton
                    plan={plan.name === "Free" ? null : plan.name.toLowerCase()}
                    label={plan.cta}
                    highlight={plan.highlight}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="mt-12 text-center text-sm text-muted-foreground">
          All plans include a 7-day free trial. Cancel anytime.
          <br />
          Break-even: 8-12 users on Plus.
        </p>
      </main>
      <Footer />
    </>
  );
}
