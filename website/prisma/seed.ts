import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import dotenv from "dotenv";

dotenv.config({ path: ".env.local" });

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

const concepts = [
  {
    slug: "prophylactic-resilience",
    name: "Prophylactic Resilience",
    summary: "Non-intuitive consolidation moves that preserve flexibility in seemingly difficult positions.",
    description: `The strong network re-evaluates opening positions as far more tenable than weaker engines believe. It plays non-intuitive consolidation moves — knight retreats, early king centralization — that preserve flexibility.

Where a weaker engine sees collapse (eval -0.53), the stronger network sees a tenable position (-0.30). The key insight: sometimes the best move looks like a step backward.

**How to recognize it:** When your position looks uncomfortable but not tactically lost, ask yourself: "Is there a retreat or regrouping move that keeps all my options open?" The answer is often a knight returning to its starting square or a king stepping to an unexpected square.

**Practice tip:** In your games, when you feel pressured in the opening, resist the urge to "do something." Look for quiet moves that maintain piece coordination.`,
    difficulty: "advanced",
    isFree: true,
    positions: [
      {
        fen: "r1bqkb1r/2pppp1p/6pn/pp2n3/P1P5/1P5N/3PPPPP/RNBQKBR1 b Qkq - 3 8",
        strongMove: "h6g8",
        weakMove: "h8g8",
        explanation: "The strong network retreats the knight to g8 — a 'backward' move that regroups forces and keeps options open. The weak network activates the rook mechanically.",
        arrows: [["h6", "g8"]],
      },
      {
        fen: "rnbqkbnr/pp1p1p1p/6p1/2p5/2PPp3/P3P3/1P3PPP/RNBQKBNR b KQkq - 0 5",
        strongMove: "e8e7",
        weakMove: "d7d5",
        explanation: "The unconventional Ke7 centralizes the king early for maximum flexibility. The obvious d5 is standard but less flexible.",
        arrows: [["e8", "e7"]],
      },
      {
        fen: "rnbqkbnr/1p4p1/7p/pPppppP1/3P4/N6B/P1PBPP1P/R2QK1NR b KQkq - 1 8",
        strongMove: "d8c7",
        weakMove: "g8e7",
        explanation: "Queen centralization on c7 provides maximum flexibility in a complex pawn structure. Standard development with Ne7 is less dynamic.",
        arrows: [["d8", "c7"]],
      },
    ],
  },
  {
    slug: "dynamic-f-file-counterattack",
    name: "Dynamic f-file Counterattack",
    summary: "Central counterattacks via f-pawn pushes that weaker engines miss in favor of wing activity.",
    description: `The strong network identifies central counterattacks via the f-file (f5/f6 pawn pushes) that weaker engines ignore in favor of wing activity like g5 or b6.

The evaluation diverges massively in certain positions: the strong network sees a slightly favorable position (+0.13) where the weaker one sees disaster (-0.45).

**How to recognize it:** When your opponent has expanded on one side of the board, look for a central f-pawn push that opens lines and creates dynamic counterplay. This is especially effective when the opponent's center is over-extended.

**Practice tip:** Before playing a wing pawn move (g5, b6, a5), always check if f5 or f6 creates more active play centrally.`,
    difficulty: "advanced",
    isFree: true,
    positions: [
      {
        fen: "rnbqkbr1/1pp1p1pp/5p1n/pP1p4/P2P1P2/8/2P1P1PP/RNBQKBNR b KQq - 0 6",
        strongMove: "f6f5",
        weakMove: "g7g5",
        explanation: "f5 is a dynamic central counterattack that opens lines. The weaker engine plays g5, a passive wing push. Evaluation gap: +0.13 vs -0.45.",
        arrows: [["f6", "f5"]],
      },
      {
        fen: "rnbq1bnr/ppppkppp/8/8/2P1pP2/1Q3N2/PP1PP1PP/RNB1KBR1 b Q - 7 10",
        strongMove: "e7e8",
        weakMove: "b7b6",
        explanation: "Ke8 is a tactical retreat that preserves the pawn structure for a future f-file counterattack. b6 fianchetto is too slow.",
        arrows: [["e7", "e8"]],
      },
      {
        fen: "r1bqkb1r/2pppppp/1pn4n/p7/3P1PP1/1P6/P1P1P2P/RNBQKBNR b KQkq - 0 5",
        strongMove: "h6g8",
        weakMove: "h6g8",
        explanation: "Both networks agree on Ng8 here, but the strong network plans to follow up with f5 while the weak network doesn't see this plan.",
        arrows: [["h6", "g8"]],
      },
    ],
  },
  {
    slug: "king-safety-over-material",
    name: "King Safety Over Material",
    summary: "Prophylactic moves that prioritize structural safety over immediate pawn captures.",
    description: `The strong network prioritizes king safety through prophylactic moves, while weaker engines grab material. The strong network understands that structural safety is worth more than a pawn.

The defining example: the strong network plays Rg1 (a prophylactic rook move that shores up the kingside) while the weaker engine plays fxe4 (winning a pawn). The strong forgoes material for structural safety.

**How to recognize it:** When you can win a pawn but your king position becomes slightly weakened, pause. Ask: "Will my king be safe after this capture?" If there's any doubt, look for a prophylactic move instead.

**Practice tip:** In your analysis, flag positions where you captured material but your king got exposed within 5 moves. These are the moments where this concept applies.`,
    difficulty: "intermediate",
    isFree: false,
    positions: [
      {
        fen: "rn2kbnr/1pq1pbp1/p1p2p2/P1Bp3p/4P3/R1NP3B/1PP2P1P/3QK1NR b Kkq - 5 12",
        strongMove: "e8d8",
        weakMove: "c7d8",
        explanation: "Kd8 tucks the king away safely. Qd8 blocks the king's escape route. Evaluation gap: +0.20 vs -0.57 — a 77-centipawn swing from one move.",
        arrows: [["e8", "d8"]],
      },
      {
        fen: "r1bqkb1r/pp1pp2p/n1p3pn/5p2/8/NPP2P2/P1QPP1PP/R1B1KBNR w KQkq - 0 6",
        strongMove: "f3f4",
        weakMove: "f3f4",
        explanation: "Both agree on f4, but the evaluation diverges: +0.44 vs -0.19. The strong network understands f4 creates a lasting space advantage.",
        arrows: [["f3", "f4"]],
      },
      {
        fen: "rnbqk2r/p1ppn2p/1p3pp1/2b5/4p2P/P1P1PP1N/1PQPB1P1/RNB1K2R w KQkq - 5 9",
        strongMove: "h1g1",
        weakMove: "f3e4",
        explanation: "Rg1 shores up the kingside prophylactically. fxe4 grabs a pawn but weakens the king. Classic safety-over-material judgment.",
        arrows: [["h1", "g1"]],
      },
    ],
  },
  {
    slug: "material-imbalance-compensation",
    name: "Material Imbalance Compensation",
    summary: "Positions with sacrificed material where the strong network sees far more compensation than expected.",
    description: `This concept spans positions with unequal material — sacrifices, gambits, and imbalances. The strong network evaluates the side with less material as having far more compensation than weaker engines believe.

The key insight: compensation for material isn't just about immediate tactical threats. It includes long-term factors like piece activity, king safety, and pawn structure that compound over many moves.

**How to recognize it:** When you're a pawn down but your pieces are active and your opponent's king is slightly exposed, the position may be far better than the material count suggests. Don't rush to win the material back — maintain the pressure.

**Practice tip:** Study classic exchange sacrifices (Petrosian, Carlsen) to develop intuition for when activity compensates for material.`,
    difficulty: "advanced",
    isFree: false,
    positions: [
      {
        fen: "r1bqk2r/pp1pn3/P3p1pb/2p2pPp/3P4/8/P1PQPP1P/R1BNKBNR w KQkq - 1 10",
        strongMove: "a6b7",
        weakMove: "c1a3",
        explanation: "axb7 is a dynamic breakthrough capture. The strong network sees the complications favor White (-0.21). The weak sees near-collapse (-0.75).",
        arrows: [["a6", "b7"]],
      },
      {
        fen: "r3k1nr/1p5p/n1p1pp2/pNbp4/5PpP/3P4/1P2P1PK/q1BQ1BRN b - - 2 19",
        strongMove: "a8c8",
        weakMove: "a8d8",
        explanation: "Rc8 centralizes the rook for maximum pressure. Rd8 is passive. The strong sees lasting compensation (-0.16) where the weak is pessimistic (-0.36).",
        arrows: [["a8", "c8"]],
      },
      {
        fen: "r1bqkbnr/p1p1p2p/1p3p2/2Qp2p1/2P5/2N5/PP1PPPPP/R1B1KBNR w KQkq - 0 6",
        strongMove: "g1f3",
        weakMove: "b2b3",
        explanation: "Nf3 develops actively with initiative. b3 is a passive fianchetto that surrenders the tempo advantage.",
        arrows: [["g1", "f3"]],
      },
    ],
  },
];

async function main() {
  console.log("Seeding concepts...");

  for (const c of concepts) {
    const { positions, ...conceptData } = c;

    const concept = await prisma.concept.upsert({
      where: { slug: c.slug },
      update: { ...conceptData, positionCount: positions.length },
      create: { ...conceptData, positionCount: positions.length },
    });

    // Delete existing positions and re-create
    await prisma.conceptPosition.deleteMany({ where: { conceptId: concept.id } });

    for (let i = 0; i < positions.length; i++) {
      await prisma.conceptPosition.create({
        data: {
          conceptId: concept.id,
          fen: positions[i].fen,
          strongMove: positions[i].strongMove,
          weakMove: positions[i].weakMove,
          explanation: positions[i].explanation,
          arrows: positions[i].arrows,
          sortOrder: i,
        },
      });
    }

    console.log(`  Seeded: ${concept.name} (${positions.length} positions)`);
  }

  console.log("Done.");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
