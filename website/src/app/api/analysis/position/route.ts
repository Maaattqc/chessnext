import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";
import { validateFen } from "@/lib/validate-fen";
import { analysisLimiter, rateLimit } from "@/lib/rate-limit";

const schema = z.object({
  fen: z.string().min(1).max(100),
  userRating: z.number().int().min(100).max(3500).default(1500),
});

const CHESS_ENGINE_URL = process.env.CHESS_ENGINE_URL || "http://localhost:8000";
const CHESS_ENGINE_INTERNAL_KEY = process.env.CHESS_ENGINE_INTERNAL_KEY || "";

// Plan limits: analyses per day
const PLAN_LIMITS: Record<string, number> = {
  free: 1,
  plus: 60,
  pro: 9999,
  coach: 9999,
};

export async function POST(req: NextRequest) {
  try {
    // Auth
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Please sign in first.", status: 401 } },
        { status: 401 }
      );
    }

    // Rate limit
    const { success: allowed } = await rateLimit(analysisLimiter, `analysis:${session.user.id}`);
    if (!allowed) {
      return NextResponse.json(
        { error: { code: "RATE_LIMITED", message: "Too many requests. Try again in a minute.", status: 429 } },
        { status: 429, headers: { "Retry-After": "60" } }
      );
    }

    // Parse input
    const body = await req.json();
    const parsed = schema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid input.", status: 400 } },
        { status: 400 }
      );
    }

    // Validate FEN
    const fenResult = validateFen(parsed.data.fen);
    if (!fenResult.valid) {
      return NextResponse.json(
        { error: { code: "INVALID_FEN", message: fenResult.error || "Invalid position.", status: 400 } },
        { status: 400 }
      );
    }

    // Check daily usage limit
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    const plan = user?.plan || "free";
    const limit = PLAN_LIMITS[plan] || 1;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const usage = await prisma.dailyUsage.findUnique({
      where: { userId_date: { userId: session.user.id, date: today } },
    });

    if ((usage?.positionAnalyses || 0) >= limit) {
      return NextResponse.json(
        { error: { code: "RATE_LIMITED", message: `Daily limit reached (${limit}/day on ${plan} plan). Upgrade for more.`, status: 429 } },
        { status: 429 }
      );
    }

    // Call chess-engine
    const engineRes = await fetch(`${CHESS_ENGINE_URL}/internal/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": CHESS_ENGINE_INTERNAL_KEY,
      },
      body: JSON.stringify({
        fen: parsed.data.fen,
        userRating: parsed.data.userRating,
        depth: 20,
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!engineRes.ok) {
      const errData = await engineRes.json().catch(() => null);
      return NextResponse.json(
        { error: { code: "ENGINE_UNAVAILABLE", message: errData?.error?.message || "Analysis engine unavailable.", status: 503 } },
        { status: 503 }
      );
    }

    const analysisResult = await engineRes.json();

    // Save analysis + update daily usage
    await Promise.all([
      prisma.analysis.create({
        data: {
          userId: session.user.id,
          type: "position",
          fen: parsed.data.fen,
          result: analysisResult,
        },
      }),
      prisma.dailyUsage.upsert({
        where: { userId_date: { userId: session.user.id, date: today } },
        create: { userId: session.user.id, date: today, positionAnalyses: 1 },
        update: { positionAnalyses: { increment: 1 } },
      }),
    ]);

    return NextResponse.json(analysisResult);
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
