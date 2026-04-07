import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { validateFen } from "@/lib/validate-fen";
import { analysisLimiter, rateLimit } from "@/lib/rate-limit";

const schema = z.object({
  fen: z.string().min(1).max(100),
  userRating: z.number().int().min(100).max(3500),
  engineBestMove: z.string().min(2).max(10),
  engineTopMoves: z.array(z.object({
    move: z.string(),
    eval: z.number(),
  })).max(10).optional(),
});

const CHESS_ENGINE_URL = process.env.CHESS_ENGINE_URL || "http://localhost:8000";
const CHESS_ENGINE_INTERNAL_KEY = process.env.CHESS_ENGINE_INTERNAL_KEY || "";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Please sign in.", status: 401 } },
        { status: 401 }
      );
    }

    const { success } = await rateLimit(analysisLimiter, `hmove:${session.user.id}`);
    if (!success) {
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

    // Call chess-engine for human-adjusted move
    const engineRes = await fetch(`${CHESS_ENGINE_URL}/internal/human-move`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": CHESS_ENGINE_INTERNAL_KEY,
      },
      body: JSON.stringify({
        fen: parsed.data.fen,
        userRating: parsed.data.userRating,
        engineBestMove: parsed.data.engineBestMove,
        engineTopMoves: parsed.data.engineTopMoves || [],
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!engineRes.ok) {
      // Fallback: return the engine's best move as the human move
      return NextResponse.json({
        move: parsed.data.engineBestMove,
        explanation: "This is the engine's top recommendation for this position.",
        adjusted: false,
      });
    }

    const result = await engineRes.json();
    return NextResponse.json({ ...result, adjusted: true });
  } catch {
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}
