"""Authentication endpoints."""

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

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import (
    LOGIN_LIMITS,
    REFRESH_LIMIT,
    REGISTER_LIMIT,
    client_ip,
    limiter,
)
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    AccountDisabled,
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
)
from app.services.rate_events import DurableLimiter, TooManyAttempts, register_bucket

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


def _clear_refresh_cookie(response: Response) -> None:
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


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


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
        user=UserResponse.model_validate(user),
        token=_token_response(access_token),
    )


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
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from exc
    except AccountDisabled as exc:
        _clear_refresh_cookie(response)
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
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse, summary="Current user")
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
