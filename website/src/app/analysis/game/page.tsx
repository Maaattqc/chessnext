"use client";

import { useState } from "react";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Search, AlertTriangle, CheckCircle, XCircle, ChevronDown, ChevronUp } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Classification = "brilliant" | "great" | "good" | "inaccuracy" | "mistake" | "blunder";

interface RootCause {
  conceptId: string;
  explanation: string;
}

interface MoveAnalysis {
  moveNumber: number;
  move: string;
  evaluation: number;
  classification: Classification;
  comment: string | null;
  rootCause?: RootCause;
}

interface GameAnalysisResult {
  id: string;
  moves: MoveAnalysis[];
  summary: string;
}

// ---------------------------------------------------------------------------
// Classification colors and labels
// ---------------------------------------------------------------------------

const CLASSIFICATION_STYLES: Record<Classification, { bg: string; text: string; label: string }> = {
  brilliant: { bg: "bg-cyan-500/20", text: "text-cyan-400", label: "Brilliant" },
  great: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Great" },
  good: { bg: "bg-green-500/20", text: "text-green-400", label: "Good" },
  inaccuracy: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Inaccuracy" },
  mistake: { bg: "bg-orange-500/20", text: "text-orange-400", label: "Mistake" },
  blunder: { bg: "bg-red-500/20", text: "text-red-400", label: "Blunder" },
};

// ---------------------------------------------------------------------------
// EvalBar component
// ---------------------------------------------------------------------------

function EvalBar({ evaluation, className }: { evaluation: number; className?: string }) {
  // Clamp eval to [-5, 5] for display, map to 0-100% white
  const clamped = Math.max(-5, Math.min(5, evaluation));
  const whitePct = ((clamped + 5) / 10) * 100;

  return (
    <div className={cn("relative h-4 w-full overflow-hidden rounded-sm bg-zinc-800", className)}>
      <div
        className="absolute inset-y-0 left-0 bg-white/90 transition-all duration-300"
        style={{ width: `${whitePct}%` }}
      />
      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold mix-blend-difference text-white">
        {evaluation > 0 ? "+" : ""}{evaluation.toFixed(2)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MoveRow component
// ---------------------------------------------------------------------------

function MoveRow({ move, isUserMove }: { move: MoveAnalysis; isUserMove: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const style = CLASSIFICATION_STYLES[move.classification];
  const hasDetail = move.comment || move.rootCause;
  const isNotable = move.classification !== "good" && move.classification !== "great" && move.classification !== "brilliant";

  return (
    <div
      className={cn(
        "border-b border-border/20 last:border-0",
        isNotable && isUserMove && style.bg
      )}
    >
      <button
        type="button"
        className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-white/5 transition-colors"
        onClick={() => hasDetail && setExpanded(!expanded)}
        disabled={!hasDetail}
      >
        {/* Move number + notation */}
        <span className="w-10 shrink-0 font-mono text-muted-foreground text-xs">
          {move.moveNumber}.{isUserMove ? "" : ".."}
        </span>
        <span className={cn("w-14 shrink-0 font-mono font-semibold", isUserMove ? "text-foreground" : "text-muted-foreground")}>
          {move.move}
        </span>

        {/* Eval bar */}
        <EvalBar evaluation={move.evaluation} className="w-24 shrink-0" />

        {/* Classification badge */}
        {isNotable && isUserMove && (
          <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", style.bg, style.text)}>
            {style.label}
          </span>
        )}

        {/* Expand indicator */}
        <span className="ml-auto">
          {hasDetail && (
            expanded
              ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
              : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </span>
      </button>

      {/* Detail panel */}
      {expanded && hasDetail && (
        <div className="px-3 pb-3 pl-12 space-y-2">
          {move.comment && (
            <p className="text-sm text-muted-foreground">{move.comment}</p>
          )}
          {move.rootCause && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 mb-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Root Cause
              </div>
              <p className="text-sm text-amber-200/80">
                {move.rootCause.explanation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function GameAnalysisPage() {
  const [pgn, setPgn] = useState("");
  const [userColor, setUserColor] = useState<"white" | "black">("white");
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<GameAnalysisResult | null>(null);

  async function handleAnalyze() {
    setError("");
    setAnalyzing(true);
    setResult(null);

    try {
      const res = await fetch("/api/analysis/game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pgn, userColor, userRating: 1500 }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error?.message || "Analysis failed.");
        return;
      }

      setResult(data);
    } catch {
      setError("Could not reach analysis engine. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  }

  // Stats derived from result
  const stats = result
    ? {
        mistakes: result.moves.filter((m) => m.classification === "mistake").length,
        blunders: result.moves.filter((m) => m.classification === "blunder").length,
        inaccuracies: result.moves.filter((m) => m.classification === "inaccuracy").length,
        totalMoves: result.moves.length,
      }
    : null;

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="mb-2 text-3xl font-bold">Game Analysis</h1>
        <p className="mb-8 text-muted-foreground">
          Paste a PGN to get root-cause analysis of your mistakes. Not just <em>where</em> you went wrong, but <em>why</em>.
        </p>

        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          {/* Input panel */}
          <div className="space-y-4">
            {/* PGN textarea */}
            <div>
              <label htmlFor="pgn-input" className="mb-2 block text-sm font-medium">
                PGN
              </label>
              <textarea
                id="pgn-input"
                rows={10}
                placeholder={"1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 ..."}
                value={pgn}
                onChange={(e) => setPgn(e.target.value)}
                className="w-full min-w-0 rounded-lg border border-input bg-transparent px-3 py-2 font-mono text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 dark:bg-input/30 resize-y"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {pgn.length} / 10,000 characters
              </p>
            </div>

            {/* Color select */}
            <div>
              <label htmlFor="color-select" className="mb-2 block text-sm font-medium">
                Your color
              </label>
              <select
                id="color-select"
                value={userColor}
                onChange={(e) => setUserColor(e.target.value as "white" | "black")}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
              >
                <option value="white">White</option>
                <option value="black">Black</option>
              </select>
            </div>

            {/* Submit */}
            <Button
              size="lg"
              className="w-full"
              onClick={handleAnalyze}
              disabled={analyzing || pgn.trim().length === 0}
            >
              <Search className="mr-2 h-4 w-4" />
              {analyzing ? "Analyzing..." : "Analyze game"}
            </Button>

            {error && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
          </div>

          {/* Results panel */}
          <div className="space-y-4">
            {/* Loading skeleton */}
            {analyzing && (
              <Card className="border-border/40">
                <CardContent className="space-y-4 pt-6">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <div className="space-y-2 pt-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <Skeleton key={i} className="h-8 w-full" />
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Summary card */}
            {result && !analyzing && (
              <>
                <Card className="border-border/40">
                  <CardHeader>
                    <CardTitle className="text-lg">Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {result.summary}
                    </p>

                    {/* Quick stats */}
                    {stats && (
                      <div className="mt-4 grid grid-cols-3 gap-3">
                        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-center">
                          <div className="text-xl font-bold text-red-400">{stats.blunders}</div>
                          <div className="text-xs text-red-400/70">Blunders</div>
                        </div>
                        <div className="rounded-md border border-orange-500/30 bg-orange-500/10 px-3 py-2 text-center">
                          <div className="text-xl font-bold text-orange-400">{stats.mistakes}</div>
                          <div className="text-xs text-orange-400/70">Mistakes</div>
                        </div>
                        <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-center">
                          <div className="text-xl font-bold text-yellow-400">{stats.inaccuracies}</div>
                          <div className="text-xs text-yellow-400/70">Inaccuracies</div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Root cause cards (pulled from moves) */}
                {result.moves
                  .filter((m) => m.rootCause)
                  .map((m, i) => (
                    <Card key={i} className="border-amber-500/30 bg-amber-500/5">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base text-amber-400">
                          <AlertTriangle className="h-4 w-4" />
                          Root Cause: Move {m.moveNumber}. {m.move}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">{m.comment}</p>
                        <p className="mt-2 text-sm text-amber-200/80">{m.rootCause!.explanation}</p>
                      </CardContent>
                    </Card>
                  ))}

                {/* Move list */}
                <Card className="border-border/40">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-lg">
                      <span>Move List</span>
                      <span className="text-xs font-normal text-muted-foreground">
                        {stats?.totalMoves} half-moves
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-y-auto">
                      {result.moves.map((move, i) => {
                        const isUserMove =
                          (userColor === "white" && i % 2 === 0) ||
                          (userColor === "black" && i % 2 === 1);
                        return (
                          <MoveRow key={i} move={move} isUserMove={isUserMove} />
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {/* Empty state */}
            {!result && !analyzing && (
              <Card className="border-border/40">
                <CardContent className="py-12 text-center">
                  <div
                    className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full"
                    style={{ backgroundColor: "rgba(139, 105, 20, 0.2)" }}
                  >
                    <CheckCircle className="h-8 w-8" style={{ color: "#c4a86e" }} />
                  </div>
                  <p className="text-sm font-medium">Paste a PGN and click Analyze</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Get root-cause analysis showing why mistakes happened, not just where.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
