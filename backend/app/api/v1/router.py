"""Aggregates all v1 endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import ai, applications, auth, health, interviews, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
