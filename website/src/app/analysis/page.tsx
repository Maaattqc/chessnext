"use client";

import { useState } from "react";
import { Chessboard } from "react-chessboard";
import { Chess } from "chess.js";
import { Navbar } from "@/components/navbar";
import { uciToSan, uciLineToSan } from "@/lib/chess-notation";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, RotateCcw } from "lucide-react";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

interface AnalysisResult {
  evaluation: {
    eval: { type: string; value: number };
    bestMove: string;
    bestLine: string[];
    depth: number;
  };
  concepts: { name: string; relevance: number }[];
  coachNarrative: string;
}

export default function AnalysisPage() {
  const [fen, setFen] = useState(STARTING_FEN);
  const [inputFen, setInputFen] = useState("");
  const [error, setError] = useState("");
  const [flipped, setFlipped] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  function handleLoadFen() {
    setError("");
    const trimmed = inputFen.trim();
    if (!trimmed) return;

    try {
      new Chess(trimmed);
      setFen(trimmed);
      setResult(null);
    } catch {
      setError("Invalid FEN position. Please check the format.");
    }
  }

  async function handleAnalyze() {
    setError("");
    setAnalyzing(true);
    setResult(null);

    try {
      const res = await fetch("/api/analysis/position", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen, userRating: 1500 }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error?.message || "Analysis failed.");
        return;
      }

      setResult(data);
    } catch {
      setError("Could not reach analysis engine. Make sure chess-engine is running on port 8000.");
    } finally {
      setAnalyzing(false);
    }
  }

  const sideToMove = fen.split(" ")[1] === "w" ? "white" : "black";

  // Build arrows from analysis result
  const arrows: { startSquare: string; endSquare: string; color: string }[] = [];
  if (result?.evaluation?.bestMove && result.evaluation.bestMove.length >= 4) {
    arrows.push({
      startSquare: result.evaluation.bestMove.slice(0, 2),
      endSquare: result.evaluation.bestMove.slice(2, 4),
      color: "rgba(245, 158, 11, 0.8)",
    });
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="mb-6 text-3xl font-bold">Analyze a Position</h1>

        <div className="grid gap-8 lg:grid-cols-2">
          {/* Board */}
          <div>
            <div className="mx-auto w-full max-w-[480px]">
              <Chessboard
                options={{
                  position: fen,
                  boardOrientation: flipped ? (sideToMove === "white" ? "black" : "white") : sideToMove,
                  arrows,
                  boardStyle: {
                    borderRadius: "8px",
                    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
                  },
                  darkSquareStyle: { backgroundColor: "#8B6914" },
                  lightSquareStyle: { backgroundColor: "#c4a86e" },
                  allowDragging: false,
                }}
              />
            </div>
            <div className="mt-3 flex justify-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFlipped(!flipped)}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Flip board
              </Button>
            </div>
          </div>

          {/* Controls + Results */}
          <div className="space-y-6">
            {/* FEN input */}
            <div>
              <label className="mb-2 block text-sm font-medium">
                FEN Position
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
                  value={inputFen}
                  onChange={(e) => setInputFen(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleLoadFen()}
                  className="font-mono text-sm"
                />
                <Button variant="outline" onClick={handleLoadFen}>
                  Load
                </Button>
              </div>
              {error && (
                <p className="mt-1 text-sm text-destructive">{error}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">
                {fen.length > 60 ? fen.slice(0, 60) + "..." : fen}
              </p>
            </div>

            {/* Analyze button */}
            <Button
              size="lg"
              className="w-full"
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              <Search className="mr-2 h-4 w-4" />
              {analyzing ? "Analyzing..." : "Analyze position"}
            </Button>

            {/* Loading skeleton */}
            {analyzing && (
              <Card className="border-border/40">
                <CardContent className="space-y-4 pt-6">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            )}

            {/* Results */}
            {result && !analyzing && (
              <div className="space-y-4">
                {/* Evaluation */}
                <Card className="border-border/40">
                  <CardHeader>
                    <CardTitle className="text-lg">Evaluation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-4">
                      <span className="text-3xl font-bold font-mono">
                        {result.evaluation.eval.type === "cp"
                          ? (result.evaluation.eval.value / 100).toFixed(2)
                          : `M${result.evaluation.eval.value}`}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        depth {result.evaluation.depth}
                      </span>
                    </div>
                    <div className="mt-2 text-sm">
                      <span className="text-muted-foreground">Best move: </span>
                      <span className="font-mono font-medium text-primary">
                        {uciToSan(fen, result.evaluation.bestMove)}
                      </span>
                    </div>
                    {result.evaluation.bestLine.length > 0 && (
                      <div className="mt-1 text-sm">
                        <span className="text-muted-foreground">Line: </span>
                        <span className="font-mono text-muted-foreground">
                          {uciLineToSan(fen, result.evaluation.bestLine).join(" ")}
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Concepts */}
                {result.concepts.length > 0 && (
                  <Card className="border-border/40">
                    <CardHeader>
                      <CardTitle className="text-lg">Matched Concepts</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {result.concepts.map((c, i) => (
                          <li key={i} className="flex items-center gap-2 text-sm">
                            <div className="h-2 w-2 rounded-full bg-primary" />
                            {c.name}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {/* Coach narrative */}
                <Card className="border-border/40">
                  <CardHeader>
                    <CardTitle className="text-lg">AI Coach</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {result.coachNarrative}
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Empty state */}
            {!result && !analyzing && (
              <Card className="border-border/40">
                <CardContent className="py-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    Load a position and click Analyze to see Stockfish evaluation,
                    matched concepts, and AI coaching insights.
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
