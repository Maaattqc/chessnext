import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

// Fallback: if Upstash is not configured, rate limiting is a no-op in dev
const isConfigured = !!(process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN);

function createLimiter(requests: number, window: string) {
  if (!isConfigured) return null;
  return new Ratelimit({
    redis: Redis.fromEnv(),
    limiter: Ratelimit.slidingWindow(requests, window as Parameters<typeof Ratelimit.slidingWindow>[1]),
    analytics: true,
  });
}

// Auth: 5 requests per 15 minutes per IP
export const authLimiter = createLimiter(5, "15 m");

// Checkout: 10 requests per minute per user
export const checkoutLimiter = createLimiter(10, "1 m");

// Analysis: 10 requests per minute (free), adjustable per plan
export const analysisLimiter = createLimiter(10, "1 m");

// General API: 100 requests per minute per IP
export const generalLimiter = createLimiter(100, "1 m");

export async function rateLimit(
  limiter: Ratelimit | null,
  identifier: string
): Promise<{ success: boolean; remaining?: number }> {
  if (!limiter) return { success: true }; // No-op in dev without Upstash

  const result = await limiter.limit(identifier);
  return { success: result.success, remaining: result.remaining };
}
