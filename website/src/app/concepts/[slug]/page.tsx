import Link from "next/link";
import { notFound } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { prisma } from "@/lib/db";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConceptTabs } from "./concept-tabs";
import { auth } from "@/auth";
import { Lock } from "lucide-react";

const difficultyColor = {
  beginner: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-400 border-red-500/20",
} as const;

export default async function ConceptDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const concept = await prisma.concept.findUnique({
    where: { slug },
    include: {
      positions: { orderBy: { sortOrder: "asc" } },
    },
  });

  if (!concept) notFound();

  // Check access: free concepts are open, paid concepts need a plan
  const session = await auth();
  let userPlan = "free";
  if (session?.user?.id) {
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    userPlan = user?.plan || "free";
  }

  const hasAccess = concept.isFree || userPlan !== "free";

  const positions = concept.positions.map((p) => ({
    id: p.id,
    fen: p.fen,
    strongMove: p.strongMove,
    weakMove: p.weakMove,
    explanation: p.explanation,
    arrows: p.arrows as string[][],
  }));

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6">
          <Badge
            variant="outline"
            className={
              difficultyColor[
                concept.difficulty as keyof typeof difficultyColor
              ] || ""
            }
          >
            {concept.difficulty}
          </Badge>
          <h1 className="mt-2 text-3xl font-bold">{concept.name}</h1>
          <p className="mt-1 text-muted-foreground">{concept.summary}</p>
        </div>

        {hasAccess ? (
          <ConceptTabs
            conceptId={concept.id}
            positions={positions}
            description={concept.description}
          />
        ) : (
          /* Locked state */
          <div className="relative">
            {/* Blurred preview */}
            <div className="pointer-events-none select-none blur-sm opacity-40">
              <div className="grid gap-8 lg:grid-cols-2">
                <div className="aspect-square max-w-[480px] rounded-lg bg-muted" />
                <div className="space-y-4">
                  <div className="h-4 w-3/4 rounded bg-muted" />
                  <div className="h-4 w-full rounded bg-muted" />
                  <div className="h-4 w-2/3 rounded bg-muted" />
                  <div className="h-4 w-full rounded bg-muted" />
                  <div className="h-4 w-1/2 rounded bg-muted" />
                </div>
              </div>
            </div>

            {/* Upgrade overlay */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="rounded-xl border border-primary/30 bg-card p-8 text-center shadow-lg">
                <Lock className="mx-auto h-10 w-10 text-primary" />
                <h2 className="mt-4 text-xl font-bold">Upgrade to unlock</h2>
                <p className="mt-2 max-w-xs text-sm text-muted-foreground">
                  This concept is available on Plus, Pro, and Coach plans.
                  Get access to all {concept.positionCount} positions and practice mode.
                </p>
                <Link href="/pricing">
                  <Button className="mt-4">View plans</Button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
