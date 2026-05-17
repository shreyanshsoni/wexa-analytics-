from fastapi import APIRouter

from app.api.v1 import api_keys, auth, dashboards, health, ingestion, organizations, saved_queries, widgets

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(api_keys.router)
api_router.include_router(ingestion.router)
api_router.include_router(dashboards.router)
api_router.include_router(widgets.router)
api_router.include_router(saved_queries.router)
