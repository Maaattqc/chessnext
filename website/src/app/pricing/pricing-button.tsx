"use client";

import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export function PricingButton({
  plan,
  label,
  highlight,
}: {
  plan: string | null;
  label: string;
  highlight: boolean;
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (!plan) {
      router.push(session ? "/concepts" : "/login");
      return;
    }

    if (!session) {
      router.push("/login");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/subscription/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();

      if (data.checkoutUrl) {
        window.location.href = data.checkoutUrl;
      } else {
        alert(data.error?.message || "Stripe not configured yet.");
      }
    } catch {
      alert("Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button
      className="w-full"
      variant={highlight ? "default" : "outline"}
      onClick={handleClick}
      disabled={loading}
    >
      {loading ? "Loading..." : label}
    </Button>
  );
}
