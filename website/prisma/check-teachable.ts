import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import dotenv from "dotenv";

dotenv.config({ path: ".env.local" });

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

async function main() {
  const concepts = await prisma.concept.findMany({
    select: { name: true, teachable: true, teachScore: true },
  });
  const t = concepts.filter((c) => c.teachable === true).length;
  const e = concepts.filter((c) => c.teachable === false).length;
  console.log(`DB: ${t} teachable, ${e} experimental, ${concepts.length} total`);
  concepts.slice(0, 5).forEach((c) => console.log(`  ${c.name}: teachable=${c.teachable} score=${c.teachScore}`));
}

main().catch(console.error).finally(() => prisma.$disconnect());
