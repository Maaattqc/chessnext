import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <>
      <Navbar />
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-24">
        <h1 className="text-6xl font-bold text-primary">404</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          This position doesn&apos;t exist on the board.
        </p>
        <div className="mt-8 flex gap-4">
          <Link href="/">
            <Button>Back to home</Button>
          </Link>
          <Link href="/concepts">
            <Button variant="outline">Browse concepts</Button>
          </Link>
        </div>
      </main>
    </>
  );
}
