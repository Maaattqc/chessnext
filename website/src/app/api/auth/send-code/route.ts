import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/db";
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

const schema = z.object({
  email: z.string().email().transform((e) => e.toLowerCase().trim()),
});

function generateCode(): string {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const parsed = schema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Invalid email address.", status: 400 } },
        { status: 400 }
      );
    }

    const { email } = parsed.data;

    // Rate limit: max 5 codes per email per 15 minutes
    const recentTokens = await prisma.verificationToken.count({
      where: {
        email,
        createdAt: { gt: new Date(Date.now() - 15 * 60 * 1000) },
      },
    });

    if (recentTokens >= 5) {
      return NextResponse.json(
        { error: { code: "RATE_LIMITED", message: "Too many attempts. Try again in 15 minutes.", status: 429 } },
        { status: 429 }
      );
    }

    // Invalidate previous unused codes for this email
    await prisma.verificationToken.updateMany({
      where: { email, used: false },
      data: { used: true },
    });

    // Generate and store new code
    const code = generateCode();
    await prisma.verificationToken.create({
      data: {
        email,
        code,
        expiresAt: new Date(Date.now() + 10 * 60 * 1000), // 10 minutes
      },
    });

    // Send email via Resend
    await resend.emails.send({
      from: "ChessNext.ai <onboarding@resend.dev>",
      to: email,
      subject: `${code} is your ChessNext.ai login code`,
      text: `Your verification code is: ${code}\n\nThis code expires in 10 minutes.\n\nIf you didn't request this, ignore this email.`,
    });

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Something went wrong.", status: 500 } },
      { status: 500 }
    );
  }
}
