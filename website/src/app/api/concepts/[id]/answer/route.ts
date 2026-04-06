import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";

const schema = z.object({
  positionId: z.string().uuid(),
  move: z.string().min(2).max(10),
});

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Please sign in.", status: 401 } },
        { status: 401 }
      );
    }

    const { id: conceptId } = await params;
    const body = await req.json();
    const parsed = schema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid input.", status: 400 } },
        { status: 400 }
      );
    }

    // Find the position
    const position = await prisma.conceptPosition.findUnique({
      where: { id: parsed.data.positionId },
    });

    if (!position || position.conceptId !== conceptId) {
      return NextResponse.json(
        { error: { code: "NOT_FOUND", message: "Position not found.", status: 404 } },
        { status: 404 }
      );
    }

    // Check if the move matches the strong move
    const userMove = parsed.data.move.toLowerCase().replace(/\s/g, "");
    const strongMove = position.strongMove.toLowerCase();
    const correct = userMove === strongMove || userMove.includes(strongMove);

    // Update concept progress
    const existing = await prisma.conceptProgress.findUnique({
      where: { userId_conceptId: { userId: session.user.id, conceptId } },
    });

    if (existing) {
      await prisma.conceptProgress.update({
        where: { id: existing.id },
        data: {
          positionsCompleted: { increment: correct ? 1 : 0 },
          correctStreak: correct ? { increment: 1 } : 0,
          score: correct
            ? Math.min(1, existing.score + 0.1)
            : Math.max(0, existing.score - 0.05),
          lastReviewed: new Date(),
          // Simple spaced repetition: next review in 1/2/4/8 days based on streak
          nextReview: new Date(
            Date.now() +
              Math.min(8, Math.pow(2, correct ? (existing.correctStreak + 1) : 0)) *
                24 * 60 * 60 * 1000
          ),
        },
      });
    } else {
      await prisma.conceptProgress.create({
        data: {
          userId: session.user.id,
          conceptId,
          positionsCompleted: correct ? 1 : 0,
          correctStreak: correct ? 1 : 0,
          score: correct ? 0.1 : 0,
          lastReviewed: new Date(),
          nextReview: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      });
    }

    return NextResponse.json({
      correct,
      strongMove: position.strongMove,
      explanation: position.explanation,
    });
  } catch {
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}
