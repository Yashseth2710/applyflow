import NextLink from "next/link";

/**
 * `next/link` with prefetching off by default.
 *
 * Next 16 prefetches routes as separate segments, and on the deployed app every
 * one of those requests comes back 404 — proven with curl: the same URL answers
 * 200 without the `Next-Router-Segment-Prefetch` header and 404 with it. Around
 * forty-five per browser session, all failing, none of them changing what the
 * user sees, because a missed prefetch just means the page is fetched on click
 * instead.
 *
 * Next 16.3 offers no switch for it. `clientSegmentCache` no longer exists —
 * the build rejects it — and `prefetchInlining: false` splits prefetches into
 * *more* requests rather than fewer. Both were tried. Turning prefetch off at
 * the link is what remains.
 *
 * The cost is small here specifically: pages are shells that fetch their data
 * client-side through TanStack Query, so prefetch was warming the RSC payload
 * and not the data behind it. The cost of leaving it was a network tab full of
 * red, which is indistinguishable from a broken app to anyone who looks.
 *
 * Pass `prefetch` explicitly to override on a link where it earns its keep.
 * When the platform serves segment prefetches properly, delete this file and
 * point the imports back at `next/link`.
 */
export function Link(props: React.ComponentProps<typeof NextLink>) {
  return <NextLink prefetch={false} {...props} />;
}

export default Link;
