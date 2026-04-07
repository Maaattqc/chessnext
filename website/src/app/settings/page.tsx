"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Crown } from "lucide-react";

interface SubStatus {
  plan: string;
  status: string;
  currentPeriodEnd: string | null;
  cancelAtPeriodEnd: boolean;
}

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [rating, setRating] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sub, setSub] = useState<SubStatus | null>(null);
  const [canceling, setCanceling] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  useEffect(() => {
    fetch("/api/user/profile")
      .then((r) => r.json())
      .then((d) => { if (d.rating) setRating(String(d.rating)); })
      .catch(() => {});
    fetch("/api/subscription/status")
      .then((r) => r.json())
      .then(setSub)
      .catch(() => {});
  }, []);

  async function handleSaveRating() {
    setSaving(true);
    setSaved(false);
    const parsed = parseInt(rating);
    if (isNaN(parsed) || parsed < 100 || parsed > 3500) return;
    await fetch("/api/user/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: parsed }),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function handleCancel() {
    if (!confirm("Cancel your subscription? You'll keep access until the end of your billing period.")) return;
    setCanceling(true);
    await fetch("/api/subscription/cancel", { method: "POST" });
    const updated = await fetch("/api/subscription/status").then((r) => r.json());
    setSub(updated);
    setCanceling(false);
  }

  if (status === "loading") return null;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-8 text-2xl font-bold">Settings</h1>

        {/* Profile */}
        <Card className="mb-6 border-border/40">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-muted-foreground">Email</label>
              <p className="font-mono text-sm">{session?.user?.email}</p>
            </div>
            <div>
              <label className="mb-1 block text-sm text-muted-foreground">Chess Rating</label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  min={100}
                  max={3500}
                  value={rating}
                  onChange={(e) => setRating(e.target.value)}
                  className="max-w-[120px]"
                />
                <Button onClick={handleSaveRating} disabled={saving} variant="outline" size="sm">
                  {saving ? "Saving..." : saved ? "Saved!" : "Save"}
                </Button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Used to adjust analysis recommendations to your level.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Subscription */}
        <Card className="border-border/40">
          <CardHeader>
            <CardTitle>Subscription</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {sub && (
              <>
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="text-primary border-primary/30">
                    <Crown className="mr-1 h-3 w-3" />
                    {sub.plan.charAt(0).toUpperCase() + sub.plan.slice(1)}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {sub.status === "active" ? "Active" : sub.status}
                  </span>
                </div>

                {sub.currentPeriodEnd && (
                  <p className="text-sm text-muted-foreground">
                    {sub.cancelAtPeriodEnd
                      ? `Cancels on ${new Date(sub.currentPeriodEnd).toLocaleDateString()}`
                      : `Renews on ${new Date(sub.currentPeriodEnd).toLocaleDateString()}`}
                  </p>
                )}

                {sub.plan === "free" ? (
                  <Button onClick={() => router.push("/pricing")} size="sm">
                    Upgrade
                  </Button>
                ) : !sub.cancelAtPeriodEnd ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                    disabled={canceling}
                    className="text-destructive border-destructive/30 hover:bg-destructive/10"
                  >
                    {canceling ? "Canceling..." : "Cancel subscription"}
                  </Button>
                ) : (
                  <p className="text-sm text-amber-400">
                    Your subscription will end at the current billing period.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </main>
      <Footer />
    </>
  );
}
