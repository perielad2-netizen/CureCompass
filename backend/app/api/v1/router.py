from fastapi import APIRouter

from app.api.v1.endpoints import admin, ai, ask_ai, auth, bookmarks, conditions, dashboard, digests, health, ingestion, notifications, research_feed

api_router_v1 = APIRouter()
api_router_v1.include_router(health.router)
api_router_v1.include_router(auth.router)
api_router_v1.include_router(admin.router)
api_router_v1.include_router(bookmarks.router)
api_router_v1.include_router(conditions.router)
api_router_v1.include_router(dashboard.router)
api_router_v1.include_router(digests.router)
api_router_v1.include_router(ingestion.router)
api_router_v1.include_router(ai.router)
api_router_v1.include_router(ask_ai.router)
api_router_v1.include_router(notifications.router)
api_router_v1.include_router(research_feed.router)
