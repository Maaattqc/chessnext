"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSendCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error?.message || "Something went wrong.");
        return;
      }

      setStep("code");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await signIn("email-code", {
        email,
        code,
        redirect: false,
      });

      if (result?.error) {
        setError("Invalid or expired code. Please try again.");
        return;
      }

      router.push("/dashboard");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm rounded-xl bg-card p-8 border border-border">
        <h1 className="mb-2 text-2xl font-bold text-foreground">
          Sign in to ChessNext
        </h1>
        <p className="mb-6 text-sm text-muted-foreground">
          {step === "email"
            ? "Enter your email to receive a verification code."
            : `We sent a 6-digit code to ${email}`}
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {step === "email" ? (
          <form onSubmit={handleSendCode}>
            <Input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mb-4"
              autoFocus
            />
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Sending..." : "Send code"}
            </Button>
          </form>
        ) : (
          <form onSubmit={handleVerifyCode}>
            <Input
              type="text"
              required
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="mb-4 text-center text-2xl font-mono tracking-widest"
              autoFocus
            />
            <Button
              type="submit"
              disabled={loading || code.length !== 6}
              className="mb-3 w-full"
            >
              {loading ? "Verifying..." : "Verify"}
            </Button>
            <button
              type="button"
              onClick={() => {
                setStep("email");
                setCode("");
                setError("");
              }}
              className="w-full text-sm text-muted-foreground hover:text-foreground"
            >
              Use a different email
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
