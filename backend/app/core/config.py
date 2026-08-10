"""Application settings, loaded from environment / .env."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/.env
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    PROJECT_NAME: str = "ApplyFlow"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    # Separate from DEBUG: echoing every statement makes test output unreadable,
    # and DEBUG is otherwise useful to leave on during development.
    SQL_ECHO: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database ----
    DATABASE_URL: str

    # ---- Auth ----
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Long enough to find the mail in a spam folder, short enough that a link
    # sitting in an inbox someone else later reads is usually already dead.
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:3000"
    # Where the reset link points. Separate from CORS_ORIGINS, which is a list
    # and describes who may call the API — this has to be one address, and
    # putting a wrong one in an email is not something a user can work around.
    FRONTEND_URL: str = "http://localhost:3000"

    # ---- Email ----
    # Unset means "no mail server": the message is written to the log instead of
    # sent. That is how development and the tests run — nothing to configure,
    # no network, and the reset link is right there in the console.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "ApplyFlow"

    # ---- Rate limiting ----
    RATE_LIMIT_ENABLED: bool = True
    # Failed logins counted against the account rather than the address, so a
    # guessing run spread across many addresses still runs out. Ten wrong
    # answers in fifteen minutes is far more than a person mistyping their own
    # password and far less than a machine needs to be useful.
    LOGIN_ATTEMPT_LIMIT: int = 10
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15
    # Password reset emails per address per hour. Low on purpose: the person
    # receiving the mail is not the person asking for it, so this is the limit
    # that stops the endpoint being used to bury someone's inbox. Three is
    # enough for a first attempt plus two "it didn't arrive" retries.
    PASSWORD_RESET_HOURLY_LIMIT: int = 3
    # Per address, per day, and durable. An account created during a burst does
    # not vanish when the host restarts, so neither should the record of having
    # created it — an in-memory count hands back a full allowance every time
    # the machine wakes up.
    REGISTER_DAILY_LIMIT: int = 10
    # Per account, and durable, so a restart does not hand back a full
    # allowance on the one endpoint that spends money.
    AI_DAILY_LIMIT: int = 60
    # Uploads are capped by count as well as by the storage quota below: the
    # quota stops the disk filling, this stops a loop hammering the database.
    UPLOAD_HOURLY_LIMIT: int = 30
    # Rows are the other way to fill a 500 MB database. Capping the size of one
    # job description bounds a request; this bounds the account. Someone
    # tracking a thousand live applications is not a real job search.
    MAX_APPLICATIONS_PER_USER: int = 1_000
    #: Per application. A stage can hold several interviews; it cannot hold 50.
    MAX_INTERVIEWS_PER_APPLICATION: int = 50
    # How many proxies sit in front of the app. 0 means requests arrive
    # directly and `request.client.host` is the caller. Behind a host that
    # terminates TLS for you it is 1. Getting this wrong is not cosmetic:
    # too low counts the whole internet as one address, too high trusts a
    # header the client wrote. See app/core/rate_limit.py.
    RATE_LIMIT_PROXY_DEPTH: int = 0

    # ---- Timezone ----
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # ---- Uploads ----
    # Four, not five, because the host rejects any request body over 4.5 MB
    # before it reaches this process. At five, a 4.6 MB resume would be refused
    # by the platform with a message we did not write and cannot change; at
    # four, the user gets our own explanation and the limit is one we enforce.
    MAX_UPLOAD_SIZE_MB: int = 4
    # Total stored bytes per account. A per-file cap alone does not stop
    # anything: uploading the same five megabytes two hundred times is well
    # inside every per-file rule and fills the free database on its own.
    MAX_STORAGE_PER_USER_MB: int = 50
    ALLOWED_UPLOAD_TYPES: str = "application/pdf"
    # "postgres" keeps files in the database, which is the only option that
    # survives a redeploy on a host with an ephemeral filesystem. "local" writes
    # to UPLOAD_DIR and is there for poking at files by hand.
    STORAGE_BACKEND: Literal["postgres", "local"] = "postgres"
    UPLOAD_DIR: str = "./uploads"

    # ---- AI ----
    # mock never touches a network, which is what tests and CI run against.
    AI_PROVIDER: Literal["mock", "ollama", "gemini"] = "mock"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    # Both default to the lite model. The preview models write slightly better
    # but carry a far smaller free allowance — measured going from working to
    # exhausted inside an afternoon, while lite kept answering. On a free tier a
    # good answer that arrives beats a better one that 429s.
    #
    # Point GEMINI_MODEL at a stronger model if the key has the quota for it.
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_FAST_MODEL: str = "gemini-3.1-flash-lite"

    #: Generations are cached, so this only bites on a first run or a regenerate.
    AI_TIMEOUT_SECONDS: int = 90

    @field_validator("JWT_SECRET")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        if v.startswith("replace-me") or len(v) < 32:
            raise ValueError(
                "JWT_SECRET is unset or too short. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return v

    @model_validator(mode="after")
    def _require_deliberate_proxy_depth(self) -> "Settings":
        """In production, RATE_LIMIT_PROXY_DEPTH has to be set on purpose.

        The default of 0 is right locally and actively harmful behind a proxy:
        every request would be counted against the proxy's address, so the whole
        world shares one allowance and the first attacker locks everyone out.
        That failure is invisible until someone is already locked out, so it is
        better as a refusal to start than as a line in a log nobody reads.

        Setting it explicitly to 0 is accepted — the objection is to inheriting
        the default without having thought about it.
        """
        if self.is_production and "RATE_LIMIT_PROXY_DEPTH" not in self.model_fields_set:
            raise ValueError(
                "RATE_LIMIT_PROXY_DEPTH must be set explicitly in production. "
                "Use 1 behind a host that terminates TLS for you (Render, a load "
                "balancer), or 0 if requests genuinely arrive directly."
            )
        return self

    @property
    def sqlalchemy_url(self) -> str:
        """Neon hands out `postgresql://`; SQLAlchemy needs the psycopg3 driver
        named explicitly, otherwise it reaches for psycopg2 and fails."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_upload_types_list(self) -> list[str]:
        return [t.strip() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def max_storage_per_user_bytes(self) -> int:
        return self.MAX_STORAGE_PER_USER_MB * 1024 * 1024

    @property
    def login_attempt_window(self) -> timedelta:
        return timedelta(minutes=self.LOGIN_ATTEMPT_WINDOW_MINUTES)

    @property
    def email_configured(self) -> bool:
        """Whether there is somewhere to actually send mail."""
        return bool(self.SMTP_HOST.strip() and self.email_from_address)

    @property
    def email_from_address(self) -> str:
        """Falls back to the SMTP username, which for Gmail is the address
        anyway — one fewer variable to get wrong."""
        return self.EMAIL_FROM.strip() or self.SMTP_USER.strip()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def ai_configured(self) -> bool:
        """Whether the selected provider has what it needs to run.

        Checked before offering AI in the UI, so a missing key reads as "not set
        up" rather than surfacing as a failed request.
        """
        if self.AI_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY.strip())
        return True


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
