"use client";

import { useState, useEffect, useCallback } from "react";
import { Chessboard } from "react-chessboard";
import { Chess } from "chess.js";
import { Button } from "@/components/ui/button";
import { uciToSan, uciLineToSan, sanToSquares } from "@/lib/chess-notation";
import { ChevronLeft, ChevronRight, RotateCcw, BarChart3, Undo2 } from "lucide-react";

interface Position {
  id: string;
  fen: string;
  strongMove: string;
  weakMove: string;
  explanation: string;
  arrows: string[][];
}

interface LineEval {
  score: number;
  mate: number | null;
  bestMove: string;
  bestLine: string[];
}

interface StockfishEval {
  score: number;
  mate: number | null;
  bestMove: string;
  bestLine: string[];
  lines: LineEval[];
  depth: number;
  loading: boolean;
}

function EvalBar({ score, mate }: { score: number; mate: number | null }) {
  let pct: number;
  if (mate !== null) {
    pct = mate > 0 ? 98 : 2;
  } else {
    pct = 50 + 50 * (2 / (1 + Math.exp(-score / 200)) - 1);
    pct = Math.max(2, Math.min(98, pct));
  }

  const label = mate !== null
    ? `M${Math.abs(mate)}`
    : `${score >= 0 ? "+" : ""}${(score / 100).toFixed(1)}`;

  return (
    <div className="flex items-center gap-2">
      <div className="relative h-6 w-full overflow-hidden rounded-full bg-neutral-800">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-white transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
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
    score: 0, mate: null, bestMove: "", bestLine: [], lines: [], depth: 0, loading: false,
  });

  // Exploration mode: user can move pieces
  const [currentFen, setCurrentFen] = useState<string | null>(null);
  const [moveHistory, setMoveHistory] = useState<string[]>([]);

  const pos = positions[index];
  const baseFen = pos?.fen || "";
  const displayFen = currentFen || baseFen;
  const isExploring = currentFen !== null;

  // Reset exploration when changing position
  useEffect(() => {
    setCurrentFen(null);
    setMoveHistory([]);
  }, [index]);

  const fetchEval = useCallback(async (fen: string) => {
    setEval((e) => ({ ...e, loading: true }));
    try {
      const res = await fetch("/api/analysis/eval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fen, multiPv: 5, depth: 14 }),
      });
      if (res.ok) {
        const data = await res.json();
        const ev = data.evaluation?.eval || {};
        const rawLines: Array<{ eval?: { type?: string; value?: number }; bestMove?: string; bestLine?: string[] }> =
          data.evaluation?.lines || [];
        const lines: LineEval[] = rawLines.map((l) => ({
          score: l.eval?.type === "cp" ? (l.eval.value ?? 0) : 0,
          mate: l.eval?.type === "mate" ? (l.eval.value ?? null) : null,
          bestMove: l.bestMove || "",
          bestLine: l.bestLine || [],
        }));
        setEval({
          score: ev.type === "cp" ? ev.value : 0,
          mate: ev.type === "mate" ? ev.value : null,
          bestMove: data.evaluation?.bestMove || "",
          bestLine: data.evaluation?.bestLine || [],
          lines,
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

  // Fetch eval when engine is toggled or position changes
  useEffect(() => {
    if (showEngine) {
      fetchEval(displayFen);
    }
  }, [showEngine, displayFen, fetchEval]);

  if (!pos) return null;

  // Use the base position's side-to-move for orientation so the board
  // doesn't flip every time the user explores a move.
  const baseSide = baseFen.split(" ")[1] === "w" ? "white" : "black";
  const orientation = flipped
    ? baseSide === "white" ? "black" : "white"
    : baseSide;

  // Handle piece drop (user moves a piece)
  function onPieceDrop(sourceSquare: string, targetSquare: string): boolean {
    try {
      const game = new Chess(displayFen);
      const move = game.move({
        from: sourceSquare,
        to: targetSquare,
        promotion: "q", // Auto-promote to queen
      });

      if (move) {
        setCurrentFen(game.fen());
        setMoveHistory((h) => [...h, move.san]);
        return true;
      }
    } catch {
      // Invalid move
    }
    return false;
  }

  // Undo last move
  function handleUndo() {
    if (moveHistory.length === 0) return;

    // Replay all moves except the last one from base FEN
    const game = new Chess(baseFen);
    const newHistory = moveHistory.slice(0, -1);
    for (const san of newHistory) {
      game.move(san);
    }

    if (newHistory.length === 0) {
      setCurrentFen(null);
    } else {
      setCurrentFen(game.fen());
    }
    setMoveHistory(newHistory);
  }

  // Reset to original position
  function handleReset() {
    setCurrentFen(null);
    setMoveHistory([]);
  }

  // Arrows: only show on base position (not while exploring)
  // Deduplicate by start+end squares to avoid React key collisions.
  const arrowMap = new Map<string, { startSquare: string; endSquare: string; color: string }>();

  if (!isExploring) {
    const strongSq = sanToSquares(baseFen, pos.strongMove);
    if (strongSq) {
      arrowMap.set(`${strongSq.from}-${strongSq.to}`, { startSquare: strongSq.from, endSquare: strongSq.to, color: "rgba(245, 158, 11, 0.8)" });
    }

    const weakSq = sanToSquares(baseFen, pos.weakMove);
    if (weakSq && pos.weakMove !== pos.strongMove) {
      const key = `${weakSq.from}-${weakSq.to}`;
      if (!arrowMap.has(key)) {
        arrowMap.set(key, { startSquare: weakSq.from, endSquare: weakSq.to, color: "rgba(220, 38, 38, 0.5)" });
      }
    }
  }

  if (showEngine && eval_.bestMove) {
    const sfSq = sanToSquares(displayFen, eval_.bestMove);
    if (sfSq) {
      const key = `${sfSq.from}-${sfSq.to}`;
      if (!arrowMap.has(key)) {
        arrowMap.set(key, { startSquare: sfSq.from, endSquare: sfSq.to, color: "rgba(59, 130, 246, 0.6)" });
      }
    }
  }

  const arrows = Array.from(arrowMap.values());

  return (
    <div>
      {/* Eval bar */}
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
            position: displayFen,
            boardOrientation: orientation,
            arrows,
            boardStyle: {
              borderRadius: "8px",
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
            },
            darkSquareStyle: { backgroundColor: "#8B6914" },
            lightSquareStyle: { backgroundColor: "#c4a86e" },
            allowDragging: true,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onPieceDrop: (args: any) =>
              onPieceDrop(args.sourceSquare, args.targetSquare || ""),
          }}
        />
      </div>

      {/* Move history (when exploring) */}
      {isExploring && (
        <div className="mx-auto mt-2 flex max-w-[480px] items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
          <span className="text-xs text-amber-400">Exploring:</span>
          <span className="flex-1 font-mono text-xs text-muted-foreground">
            {moveHistory.join(" ")}
          </span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleUndo} title="Undo">
            <Undo2 className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={handleReset}>
            Reset
          </Button>
        </div>
      )}

      {/* Controls */}
      <div className="mt-3 flex items-center justify-center gap-2">
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

      {/* Stockfish panel — multi-PV */}
      {showEngine && (eval_.lines.length > 0 || eval_.loading) && (
        <div className={`mt-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 ${eval_.loading ? "opacity-60" : ""}`}>
          <div className="flex items-center gap-2 text-xs text-blue-400">
            <BarChart3 className={`h-3 w-3 ${eval_.loading ? "animate-spin" : ""}`} />
            {eval_.loading ? "Analyzing..." : `Stockfish depth ${eval_.depth}`}
          </div>
          <div className="mt-2 space-y-1.5">
            {eval_.lines.map((line, i) => {
              const label = line.mate !== null
                ? `M${Math.abs(line.mate)}`
                : `${line.score >= 0 ? "+" : ""}${(line.score / 100).toFixed(2)}`;
              const sanLine = line.bestLine.length > 0
                ? uciLineToSan(displayFen, line.bestLine).slice(0, 6).join(" ")
                : "";
              return (
                <div key={i} className={`flex items-baseline gap-2 ${i === 0 ? "" : "opacity-70"}`}>
                  <span className={`font-mono font-bold min-w-[55px] text-right ${i === 0 ? "text-base" : "text-sm"}`}>
                    {label}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground truncate">
                    {sanLine}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Move info */}
      <div className="mt-3 rounded-lg border border-border/40 bg-card p-4">
        <div className="flex gap-4 text-sm">
          <div>
            <span className="font-mono text-amber-400">Strong: </span>
            <span className="font-mono font-bold">{pos.strongMove}</span>
          </div>
          <div>
            <span className="font-mono text-red-400">Weak: </span>
            <span className="font-mono">{pos.weakMove}</span>
          </div>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{pos.explanation}</p>
      </div>

      {/* Legend */}
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
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
        <div className="flex items-center gap-1">
          Drag pieces to explore
        </div>
      </div>
    </div>
  );
}
