from fastapi import APIRouter

from app.api.v1.router import api_router_v1

api_router = APIRouter()
api_router.include_router(api_router_v1)
