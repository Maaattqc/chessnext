import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { prisma } from "@/lib/db";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      id: "email-code",
      name: "Email Code",
      credentials: {
        email: { label: "Email", type: "email" },
        code: { label: "Code", type: "text" },
      },
      async authorize(credentials) {
        const email = credentials?.email as string;
        const code = credentials?.code as string;

        if (!email || !code) return null;

        // Find valid verification token
        const token = await prisma.verificationToken.findFirst({
          where: {
            email: email.toLowerCase().trim(),
            code,
            used: false,
            expiresAt: { gt: new Date() },
            attempts: { lt: 3 },
          },
        });

        if (!token) {
          // Increment attempts on matching email tokens
          await prisma.verificationToken.updateMany({
            where: { email: email.toLowerCase().trim(), used: false },
            data: { attempts: { increment: 1 } },
          });
          return null;
        }

        // Mark token as used
        await prisma.verificationToken.update({
          where: { id: token.id },
          data: { used: true },
        });

        // Find or create user
        let user = await prisma.user.findUnique({
          where: { email: email.toLowerCase().trim() },
        });

        if (!user) {
          user = await prisma.user.create({
            data: { email: email.toLowerCase().trim() },
          });
        }

        return { id: user.id, email: user.email };
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.email = token.email as string;
      }
      return session;
    },
  },
});
