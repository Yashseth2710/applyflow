"""Request rate limiting.

Counters live in this process's memory. That is the right choice on a free
host, which runs a single instance — there is nothing to share, and the
alternative is a paid Redis add-on. It stops being right the moment a second
instance exists: each keeps its own counters, so the effective limit multiplies
by the instance count without anything looking wrong. If this ever scales out,
that is the thing to fix, and slowapi takes a storage URI to do it.

Limits are deliberately per endpoint rather than a blanket default. A blanket
limit has to be loose enough for the chattiest endpoint, which makes it useless
on the expensive ones.
"""

import warnings
from ipaddress import ip_address, ip_network

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.security import TokenError, decode_token

# Registration is a once-in-a-lifetime act. Five an hour leaves room for a
# typo'd email and a retry, and takes account farming off the table.
REGISTER_LIMIT = "5/hour"

# Two limits on login, because they answer different questions. The per-minute
# one stops a fast script; the hourly one stops a slow one that would otherwise
# sit just under it all day. Both are far above what a person mistyping their
# own password will ever reach.
LOGIN_LIMITS = ("10/minute", "60/hour")

# Called on every page load and again whenever an access token expires, so this
# is about catching something pathological rather than policing normal use.
REFRESH_LIMIT = "30/minute"

# Asking for a reset mail sends something to a mailbox that may belong to
# someone else entirely, so the real limit is the durable one keyed on the
# address being mailed. This one only stops a single caller working through a
# list of addresses quickly.
FORGOT_PASSWORD_LIMIT = "10/hour"

# Completing a reset is cheap and idempotent, but the token is the only thing
# guarding it, so this bounds how fast one caller can try guessing at signatures.
RESET_PASSWORD_LIMIT = "20/hour"

# The only endpoint that spends money. The free Gemini allowance is measured in
# a few hundred calls a day, and answers are cached, so twenty an hour is more
# than a real session needs and well short of exhausting the quota by lunchtime.
AI_LIMIT = "20/hour"


def client_ip(request: Request) -> str:
    """The caller's address, accounting for whatever sits in front of the app.

    The host terminates TLS ahead of the process, so `request.client.host` is
    the proxy on every single request. Limiting on that would put the whole
    world in one bucket, and the first attacker would lock everyone else out.

    `X-Forwarded-For` carries the chain, but a client can send whatever it likes
    in that header and the proxy appends to it rather than replacing it. Only
    the entries the proxy itself added can be believed, so the address is
    counted in from the right by the number of proxies actually in front —
    which is why that is configuration and not a guess.
    """
    depth = settings.RATE_LIMIT_PROXY_DEPTH
    if depth > 0:
        chain = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(chain) >= depth:
            return _bucket_address(chain[-depth])
    return _bucket_address(get_remote_address(request))


def _bucket_address(address: str) -> str:
    """One IPv4 address is one bucket. One IPv6 /64 is one bucket.

    A home IPv6 connection is handed a /64 as a matter of course — eighteen
    quintillion addresses, all belonging to the same person. Counting the full
    address there means a fresh allowance for every request, which is not a
    limit at all. The /64 is the smallest block that is reliably one customer,
    so that is the unit.

    Anything unparseable is used as-is: a limit on a string nobody recognises
    is still better than no limit, and the alternative is dropping the cap for
    exactly the callers who are behaving strangely.
    """
    try:
        parsed = ip_address(address)
    except ValueError:
        return address

    if parsed.version == 6:
        return str(ip_network(f"{parsed}/64", strict=False))
    return address


def account_or_ip(request: Request) -> str:
    """Bucket by account where the request has one, by address otherwise.

    Quota is spent per account, so that is what the allowance should follow.
    Counting by address gets it wrong in both directions: an office behind one
    NAT would share a single allowance between everyone in it, and one person on
    a phone would be handed a fresh one every time the network moved them.

    The token is decoded rather than used as-is because access tokens rotate
    every fifteen minutes, and keying on the string would hand out a clean slate
    on every refresh.
    """
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            return f"user:{decode_token(token, expected_type='access')}"
        except TokenError:
            # An unusable token is not an identity. Fall through to the address,
            # or a rejected token would be a way to skip the limit entirely.
            pass
    return f"ip:{client_ip(request)}"


# Left to itself slowapi reads ./.env for its own settings, and it decodes that
# file with the platform's default codec rather than UTF-8. `.env.example`
# contains an em-dash, so on a Windows machine with a cp1252 locale copying the
# example produces a .env that crashes the app on import — before any of this
# is even used. Everything here is configured in code, so it is pointed at a
# file that does not exist and Starlette's warning about that is expected.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    limiter = Limiter(
        key_func=client_ip,
        enabled=settings.RATE_LIMIT_ENABLED,
        config_filename="slowapi-config-unused",
        # Sends X-RateLimit-* and Retry-After, so the frontend can say how long
        # the wait is instead of guessing.
        headers_enabled=True,
    )


def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Match the error shape the rest of the API uses.

    slowapi's own handler returns a bare string body, which the client parses as
    an unexpected shape and reports as "something went wrong".
    """
    # The signature is Exception because that is what add_exception_handler
    # expects; anything else reaching here is a wiring mistake, and a minute is
    # a safe thing to say when the real window is unknown.
    retry_after = 60
    if isinstance(exc, RateLimitExceeded) and exc.limit is not None:
        retry_after = exc.limit.limit.get_expiry()
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Try again in a moment."},
        headers={"Retry-After": str(retry_after)},
    )
