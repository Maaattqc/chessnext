import { notFound } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { prisma } from "@/lib/db";
import { Badge } from "@/components/ui/badge";
import { ConceptTabs } from "./concept-tabs";

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

        <ConceptTabs
          conceptId={concept.id}
          positions={positions}
          description={concept.description}
        />
      </main>
      <Footer />
    </>
  );
}
