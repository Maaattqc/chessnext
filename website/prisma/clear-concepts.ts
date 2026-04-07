import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import dotenv from "dotenv";

dotenv.config({ path: ".env.local" });

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

async function main() {
  const del1 = await prisma.conceptPosition.deleteMany();
  console.log(`Deleted ${del1.count} positions`);
  const del2 = await prisma.conceptProgress.deleteMany();
  console.log(`Deleted ${del2.count} progress records`);
  const del3 = await prisma.concept.deleteMany();
  console.log(`Deleted ${del3.count} concepts`);
  console.log("Database cleared of all concepts.");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
