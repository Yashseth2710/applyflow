import type { NextConfig } from "next";

/**
 * Where the API lives, as a connect-src entry.
 *
 * Deployed, the API is a second service behind the same domain and
 * NEXT_PUBLIC_API_URL is the relative "/api/v1" — same origin, so 'self'
 * already covers it and there is nothing to add. In development it is a
 * different port, which is a different origin, and the browser blocks every
 * request unless it is named here.
 */
function apiConnectSrc(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  try {
    return ` ${new URL(configured).origin}`;
  } catch {
    // Relative, so same-origin. new URL throws on those rather than
    // resolving them, which is why this is a try and not a startsWith check.
    return "";
  }
}

/**
 * The policy is deliberately not nonce-based.
 *
 * A nonce has to be unique per request, which means no page can be prerendered
 * — all fifteen static routes would become server-rendered on every visit, for
 * a threat this app has no opening for: nothing renders raw HTML, there is no
 * dangerouslySetInnerHTML anywhere, and React escapes everything else. What is
 * given up is the anti-XSS half of script-src; what is kept is every other
 * directive, and those are not decoration:
 *
 *   frame-ancestors  nobody can frame the app to trick a click
 *   object-src       no Flash-era plugin content, a perennial escape hatch
 *   base-uri         an injected <base> cannot repoint every relative URL
 *   form-action      a form cannot be made to post credentials elsewhere
 *   connect-src      script that does run cannot phone data home
 *
 * If the app ever renders HTML it did not write, this decision needs revisiting
 * and the cost of nonces becomes worth paying.
 */
const csp = [
  "default-src 'self'",
  // 'unsafe-eval' only outside production: the dev server's React refresh
  // needs it, and shipping it would be handing an attacker a free eval().
  process.env.NODE_ENV === "production"
    ? "script-src 'self' 'unsafe-inline'"
    : "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  // Tailwind injects styles inline, and there is no nonce to hand it.
  "style-src 'self' 'unsafe-inline'",
  // data: because avatars arrive inlined as data URIs — the access token is a
  // header, so a plain <img src> to the API would arrive unauthenticated.
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  // ws: is the dev server's hot reload socket, and only ever in development.
  `connect-src 'self'${apiConnectSrc()}${process.env.NODE_ENV === "production" ? "" : " ws: wss:"}`,
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "upgrade-insecure-requests",
].join("; ");

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          // frame-ancestors above is the modern equivalent; this is for
          // browsers that do not read it.
          { key: "X-Frame-Options", value: "DENY" },
          // The reset link lives in a URL. A full referrer is exactly how such
          // a link ends up in somebody else's access log.
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
          // No Strict-Transport-Security here. Vercel sends it for every
          // deployment already, and a second copy from the app would either
          // duplicate the header or quietly disagree with it. The API is a
          // different host and sends its own — see app/core/headers.py.
        ],
      },
    ];
  },
};

export default nextConfig;
