import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const PROTECTED_PATHS = ["/dashboard"];

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "X-XSS-Protection": "1; mode=block",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Content-Security-Policy": [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' https://fonts.gstatic.com",
    "connect-src 'self' https://api.chessnext.ai https://*.posthog.com",
    "frame-ancestors 'none'",
  ].join("; "),
};

// Only add HSTS in production
function getHeaders(isProduction: boolean) {
  const headers = { ...SECURITY_HEADERS };
  if (isProduction) {
    Object.assign(headers, {
      "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    });
  }
  return headers;
}

export async function proxy(req: NextRequest) {
  const isProduction = process.env.NODE_ENV === "production";
  const pathname = req.nextUrl.pathname;

  // Auth check for protected routes
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  if (isProtected) {
    const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
    if (!token) {
      const loginUrl = new URL("/login", req.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Apply security headers to all responses
  const response = NextResponse.next();
  const headers = getHeaders(isProduction);
  for (const [key, value] of Object.entries(headers)) {
    response.headers.set(key, value);
  }

  return response;
}

export const config = {
  matcher: [
    // Match all routes except static files and Next.js internals
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
