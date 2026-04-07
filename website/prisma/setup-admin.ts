import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import dotenv from "dotenv";

dotenv.config({ path: ".env.local" });

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

async function main() {
  // Create or update admin user with pro plan
  const adminEmail = process.env.ADMIN_EMAIL;
  if (!adminEmail) {
    console.error("ADMIN_EMAIL not set in .env.local");
    process.exit(1);
  }

  const user = await prisma.user.upsert({
    where: { email: adminEmail },
    create: { email: adminEmail, plan: "pro", rating: 1500 },
    update: { plan: "pro" },
  });
  console.log("Admin user:", user.email, "plan:", user.plan);

  // Make all concepts free (accessible to everyone)
  const updated = await prisma.concept.updateMany({
    data: { isFree: true },
  });
  console.log("Concepts set to free:", updated.count);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
