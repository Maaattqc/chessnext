import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { prisma } from "@/lib/db";
import { stripe, PLANS, PlanKey } from "@/lib/stripe";

const schema = z.object({
  plan: z.enum(["plus", "pro", "coach"]),
});

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: { code: "UNAUTHORIZED", message: "Please sign in first.", status: 401 } },
        { status: 401 }
      );
    }

    const body = await req.json();
    const parsed = schema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid plan.", status: 400 } },
        { status: 400 }
      );
    }

    const planKey = parsed.data.plan as PlanKey;
    const plan = PLANS[planKey];

    if (!plan.priceId) {
      return NextResponse.json(
        { error: { code: "INTERNAL_ERROR", message: "Stripe not configured yet.", status: 503 } },
        { status: 503 }
      );
    }

    // Get or create Stripe customer
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    if (!user) {
      return NextResponse.json(
        { error: { code: "NOT_FOUND", message: "User not found.", status: 404 } },
        { status: 404 }
      );
    }

    let customerId = user.stripeCustomerId;
    if (!customerId) {
      const customer = await stripe.customers.create({ email: user.email });
      customerId = customer.id;
      await prisma.user.update({
        where: { id: user.id },
        data: { stripeCustomerId: customerId },
      });
    }

    // Create checkout session
    const checkoutSession = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: "subscription",
      line_items: [{ price: plan.priceId, quantity: 1 }],
      success_url: `${process.env.NEXTAUTH_URL}/dashboard?upgraded=true`,
      cancel_url: `${process.env.NEXTAUTH_URL}/pricing`,
      subscription_data: {
        metadata: { userId: user.id, plan: planKey },
      },
    });

    return NextResponse.json({ checkoutUrl: checkoutSession.url });
  } catch {
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}
