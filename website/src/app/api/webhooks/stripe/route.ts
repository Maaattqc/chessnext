import { NextRequest, NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { prisma } from "@/lib/db";
import Stripe from "stripe";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const signature = req.headers.get("stripe-signature");

  if (!signature || !process.env.STRIPE_WEBHOOK_SECRET) {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Missing signature.", status: 401 } },
      { status: 401 }
    );
  }

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch {
    return NextResponse.json(
      { error: { code: "UNAUTHORIZED", message: "Invalid signature.", status: 401 } },
      { status: 401 }
    );
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      const subscriptionId = session.subscription as string;
      const sub = await stripe.subscriptions.retrieve(subscriptionId);
      const userId = sub.metadata.userId;
      const plan = sub.metadata.plan;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const subAny = sub as any;
      const periodStart = new Date((subAny.current_period_start ?? subAny.start_date ?? Date.now() / 1000) * 1000);
      const periodEnd = new Date((subAny.current_period_end ?? Date.now() / 1000 + 30 * 86400) * 1000);

      if (userId && plan) {
        await prisma.subscription.upsert({
          where: { userId },
          create: {
            userId,
            stripeSubscriptionId: subscriptionId,
            plan,
            status: "active",
            currentPeriodStart: periodStart,
            currentPeriodEnd: periodEnd,
          },
          update: {
            stripeSubscriptionId: subscriptionId,
            plan,
            status: "active",
            currentPeriodStart: periodStart,
            currentPeriodEnd: periodEnd,
          },
        });

        await prisma.user.update({
          where: { id: userId },
          data: { plan },
        });
      }
      break;
    }

    case "invoice.paid": {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const invoice = event.data.object as any;
      const subscriptionId = invoice.subscription as string;
      if (subscriptionId) {
        const sub = await stripe.subscriptions.retrieve(subscriptionId);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const subAny = sub as any;
        const periodStart = new Date((subAny.current_period_start ?? Date.now() / 1000) * 1000);
        const periodEnd = new Date((subAny.current_period_end ?? Date.now() / 1000 + 30 * 86400) * 1000);
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: subscriptionId },
          data: {
            status: "active",
            currentPeriodStart: periodStart,
            currentPeriodEnd: periodEnd,
          },
        });
      }
      break;
    }

    case "invoice.payment_failed": {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const invoice = event.data.object as any;
      const subscriptionId = invoice.subscription as string;
      if (subscriptionId) {
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: subscriptionId },
          data: { status: "past_due" },
        });
      }
      break;
    }

    case "customer.subscription.deleted": {
      const sub = event.data.object as Stripe.Subscription;
      const userId = sub.metadata.userId;
      await prisma.subscription.updateMany({
        where: { stripeSubscriptionId: sub.id },
        data: { status: "canceled" },
      });
      if (userId) {
        await prisma.user.update({
          where: { id: userId },
          data: { plan: "free" },
        });
      }
      break;
    }
  }

  return NextResponse.json({ received: true });
}
