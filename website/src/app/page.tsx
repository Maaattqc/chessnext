import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BookOpen, BarChart3, Search } from "lucide-react";

const features = [
  {
    icon: BookOpen,
    title: "Superhuman Concepts",
    description:
      "Patterns discovered in Leela's neural network that exist beyond human chess knowledge.",
  },
  {
    icon: BarChart3,
    title: "Human-Adjusted Evaluation",
    description:
      "The best move at YOUR rating, not the engine's 3600 Elo recommendation.",
  },
  {
    icon: Search,
    title: "Root-Cause Analysis",
    description:
      "Find the real positional mistake, not just the tactical blunder.",
  },
];

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        {/* Hero */}
        <section className="flex flex-col items-center justify-center px-4 py-24 text-center">
          <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Chess concepts{" "}
            <span className="text-primary">no human has ever taught</span>
          </h1>
          <p className="mt-4 max-w-xl text-lg text-muted-foreground">
            Extracted from Leela Chess Zero&apos;s neural network at 3600 Elo.
            Validated by the same method used on AlphaZero.
          </p>
          <div className="mt-8 flex gap-4">
            <Link href="/concepts">
              <Button size="lg">Start learning for free</Button>
            </Link>
            <Link href="/analysis">
              <Button size="lg" variant="outline">
                Analyze a position
              </Button>
            </Link>
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto max-w-6xl px-4 pb-24">
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((f) => (
              <Card key={f.title} className="border-border/40">
                <CardHeader>
                  <f.icon className="mb-2 h-8 w-8 text-primary" />
                  <CardTitle>{f.title}</CardTitle>
                  <CardDescription>{f.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
