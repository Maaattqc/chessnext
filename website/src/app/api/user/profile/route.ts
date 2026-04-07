import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Please sign in.", status: 401 } },
      { status: 401 }
    );
  }

  const user = await prisma.user.findUnique({ where: { id: session.user.id } });
  if (!user) {
    return NextResponse.json(
      { error: { code: "NOT_FOUND", message: "User not found.", status: 404 } },
      { status: 404 }
    );
  }

  const [conceptCount, analysisCount] = await Promise.all([
    prisma.conceptProgress.count({ where: { userId: user.id, score: { gte: 0.8 } } }),
    prisma.analysis.count({ where: { userId: user.id } }),
  ]);

  return NextResponse.json({
    id: user.id,
    email: user.email,
    plan: user.plan,
    rating: user.rating,
    createdAt: user.createdAt.toISOString(),
    stats: { conceptsCompleted: conceptCount, totalAnalyses: analysisCount },
  });
}

const patchSchema = z.object({
  rating: z.number().int().min(100).max(3500).optional(),
});

export async function PATCH(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Please sign in.", status: 401 } },
      { status: 401 }
    );
  }

  const body = await req.json();
  const parsed = patchSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: { code: "VALIDATION_ERROR", message: "Invalid input.", status: 400 } },
      { status: 400 }
    );
  }

  const updated = await prisma.user.update({
    where: { id: session.user.id },
    data: parsed.data,
  });

  return NextResponse.json({ ok: true, rating: updated.rating });
}
