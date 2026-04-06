import { Skeleton } from "@/components/ui/skeleton";

export default function ConceptsLoading() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <Skeleton className="mb-2 h-9 w-64" />
      <Skeleton className="mb-8 h-5 w-96" />
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-border/40 p-6"
          >
            <Skeleton className="mb-3 h-5 w-20" />
            <Skeleton className="mb-2 h-6 w-48" />
            <Skeleton className="mb-2 h-4 w-full" />
            <Skeleton className="h-3 w-24" />
          </div>
        ))}
      </div>
    </main>
  );
}
