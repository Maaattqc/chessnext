import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";

export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Please sign in.", status: 401 } },
      { status: 401 }
    );
  }

  const url = new URL(req.url);
  const page = Math.max(1, parseInt(url.searchParams.get("page") || "1"));
  const limit = Math.min(20, Math.max(1, parseInt(url.searchParams.get("limit") || "20")));

  const [analyses, total] = await Promise.all([
    prisma.analysis.findMany({
      where: { userId: session.user.id },
      orderBy: { createdAt: "desc" },
      take: limit,
      skip: (page - 1) * limit,
      select: { id: true, type: true, fen: true, createdAt: true },
    }),
    prisma.analysis.count({ where: { userId: session.user.id } }),
  ]);

  return NextResponse.json({
    analyses: analyses.map((a) => ({
      id: a.id,
      type: a.type,
      fen: a.fen,
      createdAt: a.createdAt.toISOString(),
    })),
    total,
    page,
    pages: Math.ceil(total / limit),
  });
}
