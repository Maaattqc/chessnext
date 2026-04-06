import Link from "next/link";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Search, BarChart3, Crown } from "lucide-react";

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");

  const userId = session.user.id;

  // Fetch real data in parallel
  const [user, conceptProgress, recentAnalyses, concepts, todayUsage] =
    await Promise.all([
      prisma.user.findUnique({ where: { id: userId } }),
      prisma.conceptProgress.findMany({
        where: { userId },
        include: { concept: true },
        orderBy: { updatedAt: "desc" },
      }),
      prisma.analysis.findMany({
        where: { userId },
        orderBy: { createdAt: "desc" },
        take: 5,
      }),
      prisma.concept.findMany({ orderBy: { sortOrder: "asc" } }),
      prisma.dailyUsage.findFirst({
        where: {
          userId,
          date: new Date(new Date().toISOString().split("T")[0]),
        },
      }),
    ]);

  const plan = user?.plan || "free";
  const completedConcepts = conceptProgress.filter((cp) => cp.score >= 0.8).length;
  const totalConcepts = concepts.length;
  const analysesToday = todayUsage?.positionAnalyses || 0;
  const overallProgress =
    totalConcepts > 0 ? Math.round((completedConcepts / totalConcepts) * 100) : 0;

  // Find next concept to study (not completed, or due for review)
  const inProgressConcept = conceptProgress.find(
    (cp) => cp.score < 0.8 && cp.positionsCompleted > 0
  );
  const nextConcept = inProgressConcept?.concept || concepts[0];

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="mt-1 text-muted-foreground">{session.user.email}</p>
          </div>
          <Badge variant="outline" className="text-primary border-primary/30">
            <Crown className="mr-1 h-3 w-3" />
            {plan.charAt(0).toUpperCase() + plan.slice(1)}
          </Badge>
        </div>

        {/* Stats grid */}
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border-border/40">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Concepts Mastered</p>
              <p className="mt-1 text-3xl font-bold">
                {completedConcepts}
                <span className="text-lg text-muted-foreground">/{totalConcepts}</span>
              </p>
            </CardContent>
          </Card>
          <Card className="border-border/40">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Overall Progress</p>
              <p className="mt-1 text-3xl font-bold">{overallProgress}%</p>
              <Progress value={overallProgress} className="mt-2" />
            </CardContent>
          </Card>
          <Card className="border-border/40">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Analyses Today</p>
              <p className="mt-1 text-3xl font-bold">{analysesToday}</p>
            </CardContent>
          </Card>
          <Card className="border-border/40">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Rating</p>
              <p className="mt-1 text-3xl font-bold">{user?.rating || 1500}</p>
            </CardContent>
          </Card>
        </div>

        {/* Action cards */}
        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Continue learning */}
          {nextConcept && (
            <Card className="border-primary/30">
              <CardHeader>
                <BookOpen className="h-6 w-6 text-primary" />
                <CardTitle className="mt-2">Continue Learning</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-medium">{nextConcept.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {nextConcept.summary}
                </p>
                <Link href={`/concepts/${nextConcept.slug}`}>
                  <Button className="mt-4 w-full" size="sm">
                    Resume
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}

          {/* Quick analyze */}
          <Card className="border-border/40">
            <CardHeader>
              <Search className="h-6 w-6 text-primary" />
              <CardTitle className="mt-2">Analyze a Position</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Paste a FEN and get Stockfish eval + AI coaching.
              </p>
              <Link href="/analysis">
                <Button className="mt-4 w-full" variant="outline" size="sm">
                  Go to Analysis
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* All concepts */}
          <Card className="border-border/40">
            <CardHeader>
              <BarChart3 className="h-6 w-6 text-primary" />
              <CardTitle className="mt-2">All Concepts</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {totalConcepts} concepts available. {completedConcepts} mastered.
              </p>
              <Link href="/concepts">
                <Button className="mt-4 w-full" variant="outline" size="sm">
                  Browse Concepts
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Recent analyses */}
        {recentAnalyses.length > 0 && (
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-semibold">Recent Analyses</h2>
            <div className="space-y-2">
              {recentAnalyses.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center justify-between rounded-lg border border-border/40 bg-card px-4 py-3"
                >
                  <div>
                    <span className="font-mono text-sm">
                      {a.fen ? (a.fen.length > 40 ? a.fen.slice(0, 40) + "..." : a.fen) : "Game analysis"}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(a.createdAt).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
