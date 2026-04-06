"use client";

import { useState } from "react";
import { Chessboard } from "react-chessboard";
import { Chess } from "chess.js";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Search, RotateCcw } from "lucide-react";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export default function AnalysisPage() {
  const [fen, setFen] = useState(STARTING_FEN);
  const [inputFen, setInputFen] = useState("");
  const [error, setError] = useState("");
  const [flipped, setFlipped] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  function handleLoadFen() {
    setError("");
    const trimmed = inputFen.trim();
    if (!trimmed) return;

    try {
      new Chess(trimmed);
      setFen(trimmed);
    } catch {
      setError("Invalid FEN position. Please check the format.");
    }
  }

  function handleAnalyze() {
    setAnalyzing(true);
    // TODO: Call /api/analysis/position when chess-engine is ready
    setTimeout(() => setAnalyzing(false), 2000);
  }

  const sideToMove = fen.split(" ")[1] === "w" ? "white" : "black";

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
                  boardStyle: {
                    borderRadius: "8px",
                    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
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
                <p className="mt-1 text-sm text-red-400">{error}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">
                Current: {fen.length > 60 ? fen.slice(0, 60) + "..." : fen}
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

            {/* Results placeholder */}
            <Card className="border-border/40">
              <CardHeader>
                <CardTitle className="text-lg">Analysis Results</CardTitle>
                <CardDescription>
                  Submit a position to see Stockfish evaluation, matched
                  concepts, and AI coach insights.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="h-2 w-2 rounded-full bg-muted" />
                    Stockfish evaluation
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="h-2 w-2 rounded-full bg-muted" />
                    Human-adjusted best move
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="h-2 w-2 rounded-full bg-muted" />
                    Matched concepts
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="h-2 w-2 rounded-full bg-muted" />
                    AI coach narrative
                  </div>
                </div>
                <p className="mt-4 text-center text-xs text-muted-foreground">
                  Chess engine integration coming soon
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </>
  );
}
