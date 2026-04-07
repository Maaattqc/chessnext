import type { Metadata } from "next";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { prisma } from "@/lib/db";
import { ConceptGrid } from "./concept-grid";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Superhuman Chess Concepts — ChessNext.ai",
  description: "Learn chess patterns extracted from Leela Chess Zero that no human coach has ever taught.",
};

export default async function ConceptsPage() {
  const concepts = await prisma.concept.findMany({
    orderBy: { sortOrder: "asc" },
  });

  const serialized = concepts.map((c) => ({
    id: c.id,
    slug: c.slug,
    name: c.name,
    summary: c.summary,
    difficulty: c.difficulty,
    positionCount: c.positionCount,
    isFree: c.isFree,
    teachable: c.teachable,
    teachScore: c.teachScore,
  }));

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Superhuman Concepts</h1>
          <p className="mt-2 text-muted-foreground">
            Patterns extracted from Leela Chess Zero that no human coach has
            ever taught. Each concept was discovered by comparing two neural
            networks 69 Elo apart.
          </p>
        </div>

        <ConceptGrid concepts={serialized} />
      </main>
      <Footer />
    </>
  );
}
