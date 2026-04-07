import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { prisma } from "@/lib/db";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Superhuman Chess Concepts — ChessNext.ai",
  description: "Learn chess patterns extracted from Leela Chess Zero that no human coach has ever taught.",
};
import { BookOpen, Lock } from "lucide-react";

const difficultyColor = {
  beginner: "bg-green-500/10 text-green-400 border-green-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-400 border-red-500/20",
} as const;

export default async function ConceptsPage() {
  const concepts = await prisma.concept.findMany({
    orderBy: { sortOrder: "asc" },
  });

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

        <div className="grid gap-4 sm:grid-cols-2">
          {concepts.map((concept) => (
            <Link key={concept.id} href={`/concepts/${concept.slug}`}>
              <Card className="h-full border-border/40 transition hover:border-primary/40 hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between">
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
                    {!concept.isFree && (
                      <Lock className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <CardTitle className="mt-2 flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-primary" />
                    {concept.name}
                  </CardTitle>
                  <CardDescription>{concept.summary}</CardDescription>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {concept.positionCount} positions
                  </p>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
