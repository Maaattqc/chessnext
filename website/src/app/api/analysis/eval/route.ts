import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { validateFen } from "@/lib/validate-fen";
import { analysisLimiter, rateLimit } from "@/lib/rate-limit";

const schema = z.object({
  fen: z.string().min(1).max(100),
  multiPv: z.number().int().min(1).max(5).default(1),
  depth: z.number().int().min(1).max(30).default(20),
});

const CHESS_ENGINE_URL = process.env.CHESS_ENGINE_URL || "http://localhost:8000";
const CHESS_ENGINE_INTERNAL_KEY = process.env.CHESS_ENGINE_INTERNAL_KEY || "";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Please sign in first.", status: 401 } },
        { status: 401 }
      );
    }

    const { success: allowed } = await rateLimit(analysisLimiter, `eval:${session.user.id}`);
    if (!allowed) {
      return NextResponse.json(
        { error: { code: "RATE_LIMITED", message: "Too many requests.", status: 429 } },
        { status: 429, headers: { "Retry-After": "60" } }
      );
    }

    const body = await req.json();
    const parsed = schema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid input.", status: 400 } },
        { status: 400 }
      );
    }

    const fenResult = validateFen(parsed.data.fen);
    if (!fenResult.valid) {
      return NextResponse.json(
        { error: { code: "INVALID_FEN", message: fenResult.error || "Invalid position.", status: 400 } },
        { status: 400 }
      );
    }

    const engineRes = await fetch(`${CHESS_ENGINE_URL}/internal/eval`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": CHESS_ENGINE_INTERNAL_KEY,
      },
      body: JSON.stringify({
        fen: parsed.data.fen,
        userRating: 1500,
        depth: parsed.data.depth,
        multiPv: parsed.data.multiPv,
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!engineRes.ok) {
      return NextResponse.json(
        { error: { code: "ENGINE_UNAVAILABLE", message: "Analysis engine unavailable.", status: 503 } },
        { status: 503 }
      );
    }

    return NextResponse.json(await engineRes.json());
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      return NextResponse.json(
        { error: { code: "ENGINE_UNAVAILABLE", message: "Analysis timed out.", status: 503 } },
        { status: 503 }
      );
    }
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}
