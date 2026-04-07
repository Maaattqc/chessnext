"use client";

import { useState, useEffect, useCallback } from "react";
import { Chessboard } from "react-chessboard";
import { Button } from "@/components/ui/button";
import { uciToSan, sanToSquares } from "@/lib/chess-notation";
import { ChevronLeft, ChevronRight, RotateCcw, BarChart3 } from "lucide-react";

interface Position {
  id: string;
  fen: string;
  strongMove: string;
  weakMove: string;
  explanation: string;
  arrows: string[][];
}

interface StockfishEval {
  score: number; // centipawns (positive = white advantage)
  mate: number | null;
  bestMove: string;
  bestLine: string[];
  depth: number;
  loading: boolean;
}

function EvalBar({ score, mate }: { score: number; mate: number | null }) {
  // Convert centipawns to a visual percentage (50% = equal)
  let pct: number;
  if (mate !== null) {
    pct = mate > 0 ? 98 : 2;
  } else {
    // Sigmoid-like mapping: ±400cp maps to ~10-90%
    pct = 50 + 50 * (2 / (1 + Math.exp(-score / 200)) - 1);
    pct = Math.max(2, Math.min(98, pct));
  }

  const label = mate !== null
    ? `M${Math.abs(mate)}`
    : `${score >= 0 ? "+" : ""}${(score / 100).toFixed(1)}`;

  return (
    <div className="flex items-center gap-2">
      <div className="relative h-6 w-full overflow-hidden rounded-full bg-neutral-800">
        {/* White portion */}
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-white transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
        {/* Black portion is the background */}
      </div>
      <span className="min-w-[50px] text-right font-mono text-xs text-muted-foreground">
        {label}
      </span>
    </div>
  );
}

export function ConceptBoard({ positions }: { positions: Position[] }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [showEngine, setShowEngine] = useState(false);
  const [eval_, setEval] = useState<StockfishEval>({
    score: 0, mate: null, bestMove: "", bestLine: [], depth: 0, loading: false,
  });

  const pos = positions[index];

  const fetchEval = useCallback(async (fen: string) => {
    setEval((e) => ({ ...e, loading: true }));
    try {
      const res = await fetch("/api/analysis/position", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen, userRating: 1500 }),
      });
      if (res.ok) {
        const data = await res.json();
        const ev = data.evaluation?.eval || {};
        setEval({
          score: ev.type === "cp" ? ev.value : 0,
          mate: ev.type === "mate" ? ev.value : null,
          bestMove: data.evaluation?.bestMove || "",
          bestLine: data.evaluation?.bestLine || [],
          depth: data.evaluation?.depth || 0,
          loading: false,
        });
      } else {
        setEval((e) => ({ ...e, loading: false }));
      }
    } catch {
      setEval((e) => ({ ...e, loading: false }));
    }
  }, []);

  useEffect(() => {
    if (showEngine && pos) {
      fetchEval(pos.fen);
    }
  }, [showEngine, index, pos, fetchEval]);

  if (!pos) return null;

  const sideToMove = pos.fen.split(" ")[1] === "w" ? "white" : "black";
  const orientation = flipped
    ? sideToMove === "white" ? "black" : "white"
    : sideToMove;

  // Arrows: amber=strong, red=weak, blue=stockfish best
  const arrows: { startSquare: string; endSquare: string; color: string }[] = [];

  const strongSq = sanToSquares(pos.fen, pos.strongMove);
  if (strongSq) {
    arrows.push({
      startSquare: strongSq.from,
      endSquare: strongSq.to,
      color: "rgba(245, 158, 11, 0.8)",
    });
  }

  const weakSq = sanToSquares(pos.fen, pos.weakMove);
  if (weakSq && pos.weakMove !== pos.strongMove) {
    arrows.push({
      startSquare: weakSq.from,
      endSquare: weakSq.to,
      color: "rgba(220, 38, 38, 0.5)",
    });
  }

  if (showEngine && eval_.bestMove) {
    // Stockfish returns UCI, try both UCI and SAN
    const sfSq = sanToSquares(pos.fen, eval_.bestMove);
    if (sfSq && (!strongSq || sfSq.from !== strongSq.from || sfSq.to !== strongSq.to)) {
      arrows.push({
        startSquare: sfSq.from,
        endSquare: sfSq.to,
        color: "rgba(59, 130, 246, 0.6)",
      });
    }
  }

  return (
    <div>
      {/* Eval bar (above board) */}
      {showEngine && (
        <div className="mx-auto mb-2 max-w-[480px]">
          {eval_.loading ? (
            <div className="h-6 animate-pulse rounded-full bg-muted" />
          ) : (
            <EvalBar score={eval_.score} mate={eval_.mate} />
          )}
        </div>
      )}

      {/* Board */}
      <div className="mx-auto w-full max-w-[480px]">
        <Chessboard
          options={{
            position: pos.fen,
            boardOrientation: orientation,
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

      {/* Controls */}
      <div className="mt-4 flex items-center justify-center gap-2">
        <Button
          variant="outline"
          size="icon"
          disabled={index === 0}
          onClick={() => setIndex(index - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="min-w-[80px] text-center text-sm text-muted-foreground">
          Position {index + 1} / {positions.length}
        </span>
        <Button
          variant="outline"
          size="icon"
          disabled={index === positions.length - 1}
          onClick={() => setIndex(index + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setFlipped(!flipped)}>
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button
          variant={showEngine ? "default" : "ghost"}
          size="icon"
          onClick={() => setShowEngine(!showEngine)}
          title="Toggle Stockfish analysis"
        >
          <BarChart3 className="h-4 w-4" />
        </Button>
      </div>

      {/* Stockfish analysis panel */}
      {showEngine && !eval_.loading && eval_.bestMove && (
        <div className="mt-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
          <div className="flex items-center gap-2 text-xs text-blue-400">
            <BarChart3 className="h-3 w-3" />
            Stockfish depth {eval_.depth}
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="font-mono text-lg font-bold">
              {eval_.mate !== null
                ? `M${Math.abs(eval_.mate)}`
                : `${eval_.score >= 0 ? "+" : ""}${(eval_.score / 100).toFixed(2)}`}
            </span>
            <span className="font-mono text-sm text-muted-foreground">
              Best: {uciToSan(pos.fen, eval_.bestMove)}
            </span>
          </div>
          {eval_.bestLine.length > 0 && (
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {eval_.bestLine.slice(0, 6).join(" ")}
            </p>
          )}
        </div>
      )}

      {/* Move info */}
      <div className="mt-3 rounded-lg border border-border/40 bg-card p-4">
        <div className="flex gap-4 text-sm">
          <div>
            <span className="font-mono text-amber-400">Strong: </span>
            <span className="font-mono font-bold">{uciToSan(pos.fen, pos.strongMove)}</span>
          </div>
          <div>
            <span className="font-mono text-red-400">Weak: </span>
            <span className="font-mono">{uciToSan(pos.fen, pos.weakMove)}</span>
          </div>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{pos.explanation}</p>
      </div>

      {/* Legend */}
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="h-2 w-4 rounded bg-amber-500/80" /> Leela strong
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-4 rounded bg-red-500/50" /> Leela weak
        </div>
        {showEngine && (
          <div className="flex items-center gap-1">
            <div className="h-2 w-4 rounded bg-blue-500/60" /> Stockfish
          </div>
        )}
      </div>
    </div>
  );
}
