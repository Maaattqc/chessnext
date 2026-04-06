import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { Navbar } from "@/components/navbar";

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) redirect("/login");

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Welcome back, {session.user.email}
        </p>
        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border border-border/40 bg-card p-6">
            <h2 className="font-semibold">Continue Learning</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Pick up where you left off with concept training.
            </p>
          </div>
          <div className="rounded-xl border border-border/40 bg-card p-6">
            <h2 className="font-semibold">Analyze a Position</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Paste a FEN and get AI-powered insights.
            </p>
          </div>
          <div className="rounded-xl border border-border/40 bg-card p-6">
            <h2 className="font-semibold">Your Stats</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              0 concepts completed. 0 analyses this month.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
