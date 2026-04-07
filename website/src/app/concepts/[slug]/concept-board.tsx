"use client";

import { useState } from "react";
import { Chessboard } from "react-chessboard";
import { Button } from "@/components/ui/button";
import { uciToSan } from "@/lib/chess-notation";
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";

interface Position {
  id: string;
  fen: string;
  strongMove: string;
  weakMove: string;
  explanation: string;
  arrows: string[][];
}

export function ConceptBoard({ positions }: { positions: Position[] }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const pos = positions[index];
  if (!pos) return null;

  const sideToMove = pos.fen.split(" ")[1] === "w" ? "white" : "black";
  const orientation = flipped
    ? sideToMove === "white" ? "black" : "white"
    : sideToMove;

  // Build arrows: amber for strong, red for weak
  const arrows: { startSquare: string; endSquare: string; color: string }[] = [];
  if (pos.strongMove.length >= 4) {
    arrows.push({
      startSquare: pos.strongMove.slice(0, 2),
      endSquare: pos.strongMove.slice(2, 4),
      color: "rgba(245, 158, 11, 0.8)",
    });
  }
  if (pos.weakMove.length >= 4 && pos.weakMove !== pos.strongMove) {
    arrows.push({
      startSquare: pos.weakMove.slice(0, 2),
      endSquare: pos.weakMove.slice(2, 4),
      color: "rgba(220, 38, 38, 0.5)",
    });
  }

  return (
    <div>
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
      </div>

      {/* Move info */}
      <div className="mt-4 rounded-lg border border-border/40 bg-card p-4">
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
    </div>
  );
}
