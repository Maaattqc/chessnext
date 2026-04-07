import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

export default async function HistoryPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");

  const analyses = await prisma.analysis.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
    take: 50,
    select: { id: true, type: true, fen: true, createdAt: true },
  });

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6 flex items-center gap-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="icon">
              <ChevronLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">Analysis History</h1>
        </div>

        {analyses.length === 0 ? (
          <div className="rounded-lg border border-border/40 bg-card py-12 text-center">
            <p className="text-muted-foreground">No analyses yet.</p>
            <Link href="/analysis">
              <Button className="mt-4" size="sm">
                Analyze your first position
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {analyses.map((a) => (
              <Link
                key={a.id}
                href={`/analysis${a.fen ? `?fen=${encodeURIComponent(a.fen)}` : ""}`}
                className="flex items-center justify-between rounded-lg border border-border/40 bg-card px-4 py-3 transition hover:border-primary/30"
              >
                <div className="flex items-center gap-3">
                  <span className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                    {a.type}
                  </span>
                  <span className="font-mono text-sm">
                    {a.fen
                      ? a.fen.length > 50
                        ? a.fen.slice(0, 50) + "..."
                        : a.fen
                      : "Game analysis"}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {new Date(a.createdAt).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </Link>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
