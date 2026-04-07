import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";
import { validatePgn } from "@/lib/validate-pgn";
import { analysisLimiter, rateLimit } from "@/lib/rate-limit";

const schema = z.object({
  pgn: z.string().min(1).max(10_000),
  userColor: z.enum(["white", "black"]),
  userRating: z.number().int().min(100).max(3500).default(1500),
});

// Plan limits: game analyses per day
// free = 0 (feature requires Plus+), plus = 5, pro = 20, coach = unlimited
const PLAN_LIMITS: Record<string, number> = {
  free: 0,
  plus: 5,
  pro: 20,
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

    // Rate limit (burst protection)
    const { success: allowed } = await rateLimit(analysisLimiter, `game-analysis:${session.user.id}`);
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

    // Validate PGN
    let validatedGame;
    try {
      validatedGame = validatePgn(parsed.data.pgn);
    } catch (err) {
      return NextResponse.json(
        { error: { code: "INVALID_PGN", message: err instanceof Error ? err.message : "Invalid PGN.", status: 400 } },
        { status: 400 }
      );
    }

    // Check plan access + daily usage limit
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    const plan = user?.plan || "free";
    const limit = PLAN_LIMITS[plan] ?? 0;

    if (limit === 0) {
      return NextResponse.json(
        { error: { code: "PLAN_REQUIRED", message: "Game analysis requires a Plus plan or higher.", status: 403 } },
        { status: 403 }
      );
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const usage = await prisma.dailyUsage.findUnique({
      where: { userId_date: { userId: session.user.id, date: today } },
    });

    if ((usage?.gameAnalyses || 0) >= limit) {
      return NextResponse.json(
        { error: { code: "RATE_LIMITED", message: `Daily limit reached (${limit}/day on ${plan} plan). Upgrade for more.`, status: 429 } },
        { status: 429 }
      );
    }

    // Build mock analysis result
    // In production this would call chess-engine /internal/analyze for each move.
    // For now, return a realistic mock based on the validated game.
    const { moves } = validatedGame;
    const { userColor, userRating } = parsed.data;

    const analysisResult = buildMockAnalysis(moves, userColor, userRating);

    // Save analysis + update daily usage
    const [savedAnalysis] = await Promise.all([
      prisma.analysis.create({
        data: {
          userId: session.user.id,
          type: "game",
          pgn: parsed.data.pgn,
          userColor,
          result: analysisResult,
        },
      }),
      prisma.dailyUsage.upsert({
        where: { userId_date: { userId: session.user.id, date: today } },
        create: { userId: session.user.id, date: today, gameAnalyses: 1 },
        update: { gameAnalyses: { increment: 1 } },
      }),
    ]);

    return NextResponse.json({
      id: savedAnalysis.id,
      ...analysisResult,
    });
  } catch (err) {
    if (err instanceof SyntaxError) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid JSON body.", status: 400 } },
        { status: 400 }
      );
    }
    console.error("Game analysis error:", err);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}

// ---------------------------------------------------------------------------
// Mock analysis builder
// ---------------------------------------------------------------------------

type Classification = "brilliant" | "great" | "good" | "inaccuracy" | "mistake" | "blunder";

interface MoveAnalysis {
  moveNumber: number;
  move: string;
  evaluation: number;
  classification: Classification;
  comment: string | null;
  rootCause?: {
    conceptId: string;
    explanation: string;
  };
}

function buildMockAnalysis(moves: string[], userColor: string, _userRating: number) {
  let eval_ = 0.2;
  const analyzedMoves: MoveAnalysis[] = [];

  // Seed a deterministic-ish mistake around move 15 for the user's color
  const mistakeIndex = Math.min(29, moves.length - 1); // ~move 15 for the user
  const blunderIndex = Math.min(45, moves.length - 1); // ~move 23

  for (let i = 0; i < moves.length; i++) {
    const isUserMove =
      (userColor === "white" && i % 2 === 0) ||
      (userColor === "black" && i % 2 === 1);

    const moveNumber = Math.floor(i / 2) + 1;
    let classification: Classification = "good";
    let comment: string | null = null;
    let rootCause: MoveAnalysis["rootCause"] | undefined;

    // Simulate eval drift
    const delta = (Math.sin(i * 0.7) * 0.15);
    eval_ += isUserMove ? delta : -delta;

    if (i === mistakeIndex && isUserMove) {
      eval_ += userColor === "white" ? -1.2 : 1.2;
      classification = "mistake";
      comment = "This move weakens the kingside pawn structure and allows the opponent to create long-term pressure.";
      rootCause = {
        conceptId: "00000000-0000-0000-0000-000000000001",
        explanation: `The real issue started earlier around move ${moveNumber - 3}. A passive piece placement created the conditions for this tactical vulnerability.`,
      };
    } else if (i === blunderIndex && isUserMove && moves.length > blunderIndex) {
      eval_ += userColor === "white" ? -2.5 : 2.5;
      classification = "blunder";
      comment = "This loses material. The knight was needed to defend the critical square.";
      rootCause = {
        conceptId: "00000000-0000-0000-0000-000000000002",
        explanation: `This blunder is connected to the earlier positional concession. Without proper piece coordination, tactical errors become inevitable.`,
      };
    } else if (Math.abs(delta) > 0.12 && isUserMove) {
      classification = "inaccuracy";
      comment = "A slightly imprecise move. The position remains roughly equal.";
    } else if (i < 6) {
      classification = "good";
    }

    analyzedMoves.push({
      moveNumber,
      move: moves[i],
      evaluation: Math.round(eval_ * 100) / 100,
      classification,
      comment,
      ...(rootCause ? { rootCause } : {}),
    });
  }

  const mistakes = analyzedMoves.filter(
    (m) => m.classification === "mistake" || m.classification === "blunder"
  );

  const summary =
    mistakes.length > 0
      ? `You played a solid game overall, but there were ${mistakes.length} critical moment${mistakes.length > 1 ? "s" : ""} that shifted the balance. The key issue was around move ${mistakes[0].moveNumber}, where a positional concession led to tactical difficulties later.`
      : "A well-played game with no major mistakes. Focus on finding even more precise moves in the middlegame.";

  return {
    moves: analyzedMoves,
    summary,
  };
}
