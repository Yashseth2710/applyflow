"""Health check response schemas."""

from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    connected: bool
    latency_ms: float | None = Field(default=None, description="Round-trip time of a real SELECT 1")
    error: str | None = Field(default=None, description="Failure reason; omitted when healthy")


class HealthResponse(BaseModel):
    status: str = Field(description='"ok" or "degraded"')
    version: str
    environment: str
    database: DatabaseHealth
