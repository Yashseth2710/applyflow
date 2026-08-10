"""Response headers that tell the browser what this app is allowed to do.

None of these fix a vulnerability on their own. What they do is remove whole
categories of trouble that depend on the browser being permissive: a page
framing the API to trick someone into clicking it, a JSON response sniffed as
HTML and executed, a full URL leaking into a third party's logs through a
referrer.

They are cheap, they cannot break a correct client, and every one of them is
here because leaving it out is a decision too.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

#: An API serves JSON and nothing else, so it may load nothing at all. This is
#: not the frontend's policy — that one has a page to render and lives in
#: next.config.ts. The pair that matters here is frame-ancestors and
#: sandbox-free defaults: even the /docs page, which does load scripts, is off
#: in production.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

#: Relaxed enough for Swagger UI, which loads its own script and stylesheet from
#: a CDN and inlines its bootstrap. Only ever used outside production, where the
#: docs are switched off entirely.
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'"
)

#: Two years, and only ever sent over HTTPS. Long because a short max-age is
#: barely better than none: the guarantee is "never speak plain HTTP to this
#: host again", and it is worth little if it expires while the user is away.
HSTS = "max-age=63072000; includeSubDomains"

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Stops a browser second-guessing Content-Type. Without it, a JSON
        # response containing something that reads like markup can be sniffed
        # as HTML and executed on our own origin.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # frame-ancestors is the modern form and X-Frame-Options the one older
        # browsers understand. Both, because they cost one line.
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Send the origin to other sites, the full URL only to ourselves. A
        # reset link lives in a URL, and a full referrer is how such links end
        # up in someone else's access log.
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Nothing here uses a camera, a microphone or a location, so nothing
        # should be able to ask.
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        if request.url.path.startswith(DOCS_PATHS):
            response.headers.setdefault("Content-Security-Policy", DOCS_CSP)
        else:
            response.headers.setdefault("Content-Security-Policy", API_CSP)

        # Only in production, and only over HTTPS. Sent from a plain-HTTP
        # localhost it would pin the whole of localhost to HTTPS in the
        # developer's browser, which then breaks every other project on the
        # machine and is remarkably annoying to undo.
        if settings.is_production and _is_https(request):
            response.headers.setdefault("Strict-Transport-Security", HSTS)

        return response


def _is_https(request: Request) -> bool:
    """The host terminates TLS, so `request.url.scheme` is http on every real
    request and checking it alone would mean never sending HSTS at all.

    `x-forwarded-proto` is written by the client on the way in, unlike the
    address chain this is not defended against — and it does not need to be.
    The worst a lie achieves is an HSTS header on a response the liar already
    controls, which pins their own browser to HTTPS.
    """
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return (forwarded or request.url.scheme) == "https"
