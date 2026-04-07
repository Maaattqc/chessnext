"use client";

import { useState, useCallback } from "react";
import { Chessboard } from "react-chessboard";
import { Button } from "@/components/ui/button";
import { ChevronRight, Check, X, RotateCcw } from "lucide-react";
import { uciToSan } from "@/lib/chess-notation";

interface Position {
  id: string;
  fen: string;
  strongMove: string;
  weakMove: string;
  explanation: string;
}

interface PracticeResult {
  correct: boolean;
  strongMove: string;
  explanation: string;
}

export function ConceptPractice({
  conceptId,
  positions,
}: {
  conceptId: string;
  positions: Position[];
}) {
  const [index, setIndex] = useState(0);
  const [selectedFrom, setSelectedFrom] = useState<string | null>(null);
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const pos = positions[index];
  if (!pos) return null;

  const sideToMove = pos.fen.split(" ")[1] === "w" ? "white" : "black";

  const submitMove = useCallback(
    async (move: string) => {
      setLoading(true);
      try {
        const res = await fetch(`/api/concepts/${conceptId}/answer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ positionId: pos.id, move }),
        });
        const data = await res.json();
        if (res.ok) {
          setResult(data);
          setScore((s) => ({
            correct: s.correct + (data.correct ? 1 : 0),
            total: s.total + 1,
          }));
        }
      } catch {
        // Silently handle — user can retry
      } finally {
        setLoading(false);
      }
    },
    [conceptId, pos.id]
  );

  function handleSquareClick(square: string) {
    if (result || loading) return;

    if (!selectedFrom) {
      setSelectedFrom(square);
    } else {
      const move = selectedFrom + square;
      setSelectedFrom(null);
      submitMove(move);
    }
  }

  function handleNext() {
    setResult(null);
    setSelectedFrom(null);
    setIndex((i) => Math.min(i + 1, positions.length - 1));
  }

  function handleReset() {
    setResult(null);
    setSelectedFrom(null);
    setIndex(0);
    setScore({ correct: 0, total: 0 });
  }

  // Highlight selected square
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (selectedFrom) {
    squareStyles[selectedFrom] = { backgroundColor: "rgba(245, 158, 11, 0.4)" };
  }

  // Show correct/wrong arrows after answer
  const arrows: { startSquare: string; endSquare: string; color: string }[] = [];
  if (result) {
    const sm = result.strongMove;
    if (sm.length >= 4) {
      arrows.push({
        startSquare: sm.slice(0, 2),
        endSquare: sm.slice(2, 4),
        color: "rgba(245, 158, 11, 0.8)",
      });
    }
  }

  const isFinished = index >= positions.length - 1 && result !== null;

  return (
    <div>
      {/* Score */}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Position {index + 1} / {positions.length}
        </span>
        <span className="text-sm font-medium">
          Score: {score.correct}/{score.total}
        </span>
      </div>

      {/* Board */}
      <div className="mx-auto w-full max-w-[480px]">
        <Chessboard
          options={{
            position: pos.fen,
            boardOrientation: sideToMove,
            arrows,
            squareStyles,
            boardStyle: {
              borderRadius: "8px",
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
              cursor: result ? "default" : "pointer",
            },
            darkSquareStyle: { backgroundColor: "#8B6914" },
            lightSquareStyle: { backgroundColor: "#c4a86e" },
            allowDragging: false,
            onSquareClick: ({ square }: { square: string }) =>
              handleSquareClick(square),
          }}
        />
      </div>

      {/* Prompt */}
      {!result && !loading && (
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Click the <strong>from</strong> square, then the <strong>to</strong>{" "}
          square to make your move.
          {selectedFrom && (
            <span className="block mt-1 text-primary">
              Selected: {selectedFrom} — now click the destination
            </span>
          )}
        </p>
      )}

      {loading && (
        <p className="mt-4 text-center text-sm text-muted-foreground animate-pulse">
          Checking...
        </p>
      )}

      {/* Result feedback */}
      {result && (
        <div
          className={`mt-4 rounded-lg border p-4 ${
            result.correct
              ? "border-primary/30 bg-primary/5"
              : "border-destructive/30 bg-destructive/5"
          }`}
        >
          <div className="flex items-center gap-2">
            {result.correct ? (
              <Check className="h-5 w-5 text-primary" />
            ) : (
              <X className="h-5 w-5 text-destructive" />
            )}
            <span className="font-medium">
              {result.correct ? "Correct!" : "Not quite."}
            </span>
            <span className="ml-auto font-mono text-sm text-muted-foreground">
              Best: {uciToSan(pos.fen, result.strongMove)}
            </span>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {result.explanation}
          </p>

          {!isFinished ? (
            <Button className="mt-3" size="sm" onClick={handleNext}>
              Next position
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <div className="mt-3 space-y-2">
              <p className="text-sm font-medium">
                Practice complete! Score: {score.correct}/{score.total} (
                {Math.round((score.correct / Math.max(score.total, 1)) * 100)}%)
              </p>
              <Button size="sm" variant="outline" onClick={handleReset}>
                <RotateCcw className="mr-1 h-4 w-4" />
                Try again
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
