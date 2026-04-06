import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-border/40 bg-card">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-8 sm:flex-row sm:justify-between">
        <div className="text-sm text-muted-foreground">
          <span className="font-semibold text-primary">ChessNext</span>
          <span>.ai</span>
          <span className="ml-2">— Superhuman chess concepts from Leela Chess Zero</span>
        </div>
        <nav className="flex gap-6 text-sm text-muted-foreground">
          <Link href="/concepts" className="hover:text-foreground">
            Concepts
          </Link>
          <Link href="/analysis" className="hover:text-foreground">
            Analysis
          </Link>
          <Link href="/pricing" className="hover:text-foreground">
            Pricing
          </Link>
        </nav>
      </div>
    </footer>
  );
}
