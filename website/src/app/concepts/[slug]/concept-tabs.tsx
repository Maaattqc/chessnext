"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConceptBoard } from "./concept-board";
import { ConceptPractice } from "./concept-practice";
import { BookOpen, Target } from "lucide-react";

interface Position {
  id: string;
  fen: string;
  strongMove: string;
  weakMove: string;
  explanation: string;
  arrows: string[][];
}

export function ConceptTabs({
  conceptId,
  positions,
  description,
}: {
  conceptId: string;
  positions: Position[];
  description: string;
}) {
  return (
    <Tabs defaultValue="learn">
      <TabsList>
        <TabsTrigger value="learn">
          <BookOpen className="mr-2 h-4 w-4" />
          Learn
        </TabsTrigger>
        <TabsTrigger value="practice">
          <Target className="mr-2 h-4 w-4" />
          Practice
        </TabsTrigger>
      </TabsList>

      <TabsContent value="learn" className="mt-6">
        <div className="grid gap-8 lg:grid-cols-2">
          <ConceptBoard positions={positions} />
          <div className="max-w-none text-sm leading-relaxed text-muted-foreground">
            {description.split("\n\n").map((para, i) => {
              if (para.startsWith("**")) {
                const parts = para.split("**");
                return (
                  <p key={i} className="mb-4">
                    {parts.map((part, j) =>
                      j % 2 === 1 ? (
                        <strong key={j} className="text-foreground">{part}</strong>
                      ) : (
                        <span key={j}>{part}</span>
                      )
                    )}
                  </p>
                );
              }
              return (
                <p key={i} className="mb-4">
                  {para}
                </p>
              );
            })}
          </div>
        </div>
      </TabsContent>

      <TabsContent value="practice" className="mt-6">
        <div className="mx-auto max-w-lg">
          <p className="mb-6 text-center text-sm text-muted-foreground">
            Find the move the stronger network plays. Click the from-square,
            then the to-square.
          </p>
          <ConceptPractice conceptId={conceptId} positions={positions} />
        </div>
      </TabsContent>
    </Tabs>
  );
}
