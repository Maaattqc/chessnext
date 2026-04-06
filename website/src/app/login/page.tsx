"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

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
    <div className="flex min-h-screen items-center justify-center bg-[hsl(220,20%,8%)]">
      <div className="w-full max-w-sm rounded-xl bg-[hsl(220,20%,12%)] p-8">
        <h1 className="mb-2 text-2xl font-bold text-[hsl(210,20%,92%)]">
          Sign in to ChessNext
        </h1>
        <p className="mb-6 text-sm text-[hsl(215,15%,55%)]">
          {step === "email"
            ? "Enter your email to receive a verification code."
            : `We sent a 6-digit code to ${email}`}
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        {step === "email" ? (
          <form onSubmit={handleSendCode}>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mb-4 w-full rounded-lg border border-[hsl(215,15%,25%)] bg-[hsl(220,20%,8%)] px-4 py-3 text-[hsl(210,20%,92%)] placeholder-[hsl(215,15%,40%)] focus:border-[hsl(160,70%,45%)] focus:outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-[hsl(160,70%,45%)] px-4 py-3 font-medium text-white transition hover:bg-[hsl(160,70%,38%)] disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send code"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyCode}>
            <input
              type="text"
              required
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="mb-4 w-full rounded-lg border border-[hsl(215,15%,25%)] bg-[hsl(220,20%,8%)] px-4 py-3 text-center text-2xl font-mono tracking-widest text-[hsl(210,20%,92%)] placeholder-[hsl(215,15%,40%)] focus:border-[hsl(160,70%,45%)] focus:outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="mb-3 w-full rounded-lg bg-[hsl(160,70%,45%)] px-4 py-3 font-medium text-white transition hover:bg-[hsl(160,70%,38%)] disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Verify"}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("email");
                setCode("");
                setError("");
              }}
              className="w-full text-sm text-[hsl(215,15%,55%)] hover:text-[hsl(210,20%,92%)]"
            >
              Use a different email
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
