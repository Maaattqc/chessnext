import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";

dotenv.config({ path: ".env.local" });

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

interface NamedConcept {
  name: string;
  summary: string;
  description: string;
  difficulty: string;
  teachable?: boolean;
  avg_teach?: number;
  positions: { fen: string; strong_line: string[]; weak_line: string[] }[];
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

async function main() {
  const dataPath = path.join(__dirname, "..", "..", "tools", "named_concepts_v4.json");
  const concepts: NamedConcept[] = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

  console.log(`Seeding ${concepts.length} MCTS concepts...`);

  // Clear old data
  await prisma.conceptPosition.deleteMany();
  await prisma.conceptProgress.deleteMany();
  await prisma.concept.deleteMany();
  console.log("  Cleared old data");

  for (let i = 0; i < concepts.length; i++) {
    const c = concepts[i];
    let slug = slugify(c.name);
    // Avoid duplicate slugs
    const existing = await prisma.concept.findUnique({ where: { slug } });
    if (existing) slug = `${slug}-${i + 1}`;
    const isFree = i < 5; // First 5 free

    const concept = await prisma.concept.create({
      data: {
        slug,
        name: c.name,
        summary: c.summary,
        description: c.description,
        difficulty: c.difficulty,
        positionCount: c.positions.length,
        sortOrder: i,
        isFree,
        teachable: c.teachable !== false,
        teachScore: c.avg_teach ?? 0,
      },
    });

    for (let j = 0; j < c.positions.length; j++) {
      const p = c.positions[j];
      const strongLine = p.strong_line.join(" ");
      const weakLine = p.weak_line.join(" ");

      await prisma.conceptPosition.create({
        data: {
          conceptId: concept.id,
          fen: p.fen,
          strongMove: p.strong_line[0] || "?",
          weakMove: p.weak_line[0] || "?",
          explanation: `Optimal line: ${strongLine}\nSuboptimal line: ${weakLine}\n\n${c.summary}`,
          arrows: JSON.stringify([]),
          sortOrder: j,
        },
      });
    }

    console.log(`  ${i + 1}. ${c.name} (${isFree ? "free" : "paid"}, ${c.teachable !== false ? "teachable" : "experimental"})`);
  }

  console.log(`\nDone. ${concepts.length} concepts seeded.`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
