"""Authentication endpoints."""

import time
from datetime import timedelta

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_storage
from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.rate_limit import (
    FORGOT_PASSWORD_LIMIT,
    LOGIN_LIMITS,
    REFRESH_LIMIT,
    REGISTER_LIMIT,
    RESET_PASSWORD_LIMIT,
    client_ip,
    limiter,
)
from app.core.storage import Storage
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    AccountDisabled,
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidResetToken,
)
from app.services.rate_events import DurableLimiter, TooManyAttempts, register_bucket
from app.services.user import UserService

router = APIRouter()

REFRESH_COOKIE_NAME = "applyflow_refresh"
# Scoped to the auth routes so the cookie is not attached to every API call —
# it is only ever needed by /refresh and /logout.
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"

# A readable companion flag carrying no secret. The refresh cookie is httpOnly
# by design, so the frontend cannot tell whether a session exists and would call
# /refresh on every page load — a wasted round-trip and a console 401 for every
# logged-out visitor. This lets the client skip that call. It is only a hint:
# forging it grants nothing, since the real token is still required.
SESSION_HINT_COOKIE_NAME = "applyflow_session"


def _cookie_max_age() -> int:
    return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=_cookie_max_age(),
        # httponly: unreadable by JavaScript, so XSS cannot steal the session.
        httponly=True,
        # secure: HTTPS only. Disabled in development because localhost is HTTP.
        secure=settings.is_production,
        # lax: sent on top-level navigation but not cross-site POSTs, which
        # blocks the basic CSRF case while keeping normal use working.
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )
    response.set_cookie(
        key=SESSION_HINT_COOKIE_NAME,
        value="1",
        max_age=_cookie_max_age(),
        httponly=False,  # deliberately readable — carries no secret
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
    response.delete_cookie(
        key=SESSION_HINT_COOKIE_NAME,
        path="/",
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
    )


#: Floor on how long /forgot-password takes, in seconds.
#:
#: The endpoint answers 204 whether or not the address has an account, but
#: sending a mail takes about a second and not sending one takes none. Left
#: alone, that difference answers by stopwatch the question the status code
#: deliberately does not. A floor costs a second on an endpoint people reach
#: once, and only leaks when a send runs slower than it — a far smaller signal
#: than "instant means no account".
MIN_FORGOT_PASSWORD_SECONDS = 1.5


def _pad_to(started: float, seconds: float) -> None:
    remaining = seconds - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _user_with_avatar(user: User, db: Session, storage: Storage) -> UserResponse:
    """The picture is read from storage, so it cannot come from the model on
    its own. Signing in has to include it or the header shows initials until
    something else refreshes the session."""
    response = UserResponse.model_validate(user)
    response.avatar = UserService(db, storage).avatar_data_uri(user)
    return response


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
@limiter.limit(REGISTER_LIMIT)
def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    # Two layers on the same endpoint. The in-memory one above absorbs a flood
    # cheaply; this one is what an account-farming run actually runs into,
    # because it is still there after the host has slept and woken up.
    limits = DurableLimiter(db)
    bucket = register_bucket(client_ip(request))
    window = timedelta(days=1)
    try:
        limits.check(bucket, limit=settings.REGISTER_DAILY_LIMIT, window=window)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many accounts created from here recently.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    service = AuthService(db)
    try:
        user = service.register(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            timezone=payload.timezone,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc

    # Counted only once an account actually exists. A rejected attempt — a
    # duplicate email, say — created nothing, so charging for it would let
    # someone spend a household's allowance retyping an address they already
    # used.
    limits.record(bucket, window=window)

    access_token, refresh_token = service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=_token_response(access_token),
    )


@router.post("/login", response_model=AuthResponse, summary="Log in")
@limiter.limit(LOGIN_LIMITS[0])
@limiter.limit(LOGIN_LIMITS[1])
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> AuthResponse:
    service = AuthService(db)
    try:
        user = service.authenticate(email=payload.email, password=payload.password)
    except TooManyAttempts as exc:
        # Deliberately the same wording whether or not the account exists, for
        # the same reason the 401 below is.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Try again shortly.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except InvalidCredentials as exc:
        # One message for both "unknown email" and "wrong password" — telling
        # them apart would confirm which addresses are registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        ) from exc
    except AccountDisabled as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        ) from exc

    access_token, refresh_token = service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        user=_user_with_avatar(user, db, storage),
        token=_token_response(access_token),
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Send a password reset link",
)
@limiter.limit(FORGOT_PASSWORD_LIMIT)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    # Unused here, and not optional: slowapi writes its X-RateLimit headers onto
    # this object, and raises if the endpoint it is decorating does not have
    # one. The suite runs with limiting off, so that only shows up when the app
    # is actually running — as a 500 with no CORS header on it.
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    """Always 204, whether or not the address has an account.

    Anything else — a 404, a different message, even a noticeably faster
    response — turns this into a way to ask whether a given person has an
    account here, which login and registration both refuse to answer.
    """
    started = time.monotonic()

    service = AuthService(db)
    try:
        message = service.request_password_reset(email=payload.email)
    except TooManyAttempts as exc:
        # Safe to report, unlike the 404 above: the count is kept for unknown
        # addresses too, so hitting the limit reveals nothing either way.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset emails requested for that address. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    if message is not None:
        # Sent inline rather than as a background task. On a serverless host
        # the process can be frozen the moment the response goes out, and work
        # queued for "after" may simply never happen — a reset email that
        # silently fails to arrive is worse than a slower request.
        send_email(to=message.to, subject=message.subject, body=message.body)

    # Sending takes about a second, and not sending takes none, which would
    # answer by stopwatch the question the 204 refuses to answer in words.
    # Both paths are held to the same floor instead.
    _pad_to(started, MIN_FORGOT_PASSWORD_SECONDS)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password using a reset link",
)
@limiter.limit(RESET_PASSWORD_LIMIT)
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    response: Response,  # required by the limiter decorator; see forgot_password
    db: Session = Depends(get_db),
) -> None:
    """Deliberately does not sign the user in.

    A link from an email is weaker evidence than a password, and the reset page
    is the one place a stale link is most likely to be opened by the wrong
    person. Sending them to the login page to use the password they just chose
    costs one form and keeps sessions coming from one place.
    """
    service = AuthService(db)
    try:
        service.reset_password(token=payload.token, new_password=payload.password)
    except InvalidResetToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Request a new one.",
        ) from exc
    except AccountDisabled as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange the refresh cookie for a new access token",
)
@limiter.limit(REFRESH_LIMIT)
def refresh(
    request: Request,
    response: Response,
    applyflow_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not applyflow_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    service = AuthService(db)
    try:
        user = service.user_from_refresh_token(applyflow_refresh)
    except InvalidRefreshToken as exc:
        # Clear the bad cookie so the browser stops resending it.
        clear_session_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from exc
    except AccountDisabled as exc:
        clear_session_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        ) from exc

    access_token, new_refresh_token = service.issue_tokens(user)
    # Rotate the refresh token on every use, so a stolen one has a short
    # useful life.
    _set_refresh_cookie(response, new_refresh_token)

    return _token_response(access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out")
def logout(response: Response) -> None:
    clear_session_cookies(response)


@router.get("/me", response_model=UserResponse, summary="Current user")
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> UserResponse:
    return _user_with_avatar(current_user, db, storage)
