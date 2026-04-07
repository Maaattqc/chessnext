"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BookOpen, Lock, FlaskConical, Check } from "lucide-react";

interface ConceptItem {
  id: string;
  slug: string;
  name: string;
  summary: string;
  difficulty: string;
  positionCount: number;
  isFree: boolean;
  teachable: boolean;
  teachScore: number;
}

const difficultyColor = {
  beginner: "bg-green-500/10 text-green-400 border-green-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-400 border-red-500/20",
} as const;

export function ConceptGrid({ concepts }: { concepts: ConceptItem[] }) {
  const [filter, setFilter] = useState<"all" | "teachable" | "experimental">("all");

  const filtered = concepts.filter((c) => {
    if (filter === "teachable") return c.teachable;
    if (filter === "experimental") return !c.teachable;
    return true;
  });

  const teachableCount = concepts.filter((c) => c.teachable).length;
  const experimentalCount = concepts.filter((c) => !c.teachable).length;

  return (
    <>
      <div className="mb-6 flex items-center gap-2">
        <Button
          variant={filter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          All ({concepts.length})
        </Button>
        <Button
          variant={filter === "teachable" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("teachable")}
        >
          <Check className="mr-1 h-3 w-3" />
          Teachable ({teachableCount})
        </Button>
        <Button
          variant={filter === "experimental" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("experimental")}
        >
          <FlaskConical className="mr-1 h-3 w-3" />
          Experimental ({experimentalCount})
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {filtered.map((concept) => (
          <Link key={concept.id} href={`/concepts/${concept.slug}`}>
            <Card className="h-full border-border/40 transition hover:border-primary/40 hover:shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={
                        difficultyColor[
                          concept.difficulty as keyof typeof difficultyColor
                        ] || ""
                      }
                    >
                      {concept.difficulty}
                    </Badge>
                    {!concept.teachable && (
                      <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                        <FlaskConical className="mr-1 h-3 w-3" />
                        experimental
                      </Badge>
                    )}
                  </div>
                  {!concept.isFree && (
                    <Lock className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <CardTitle className="mt-2 flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary" />
                  {concept.name}
                </CardTitle>
                <CardDescription>{concept.summary}</CardDescription>
                <p className="mt-2 text-xs text-muted-foreground">
                  {concept.positionCount} positions
                </p>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
