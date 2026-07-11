from fastapi import APIRouter
from app.api.v1.notifications import router as notifications_router
from app.api.v1.users import router as users_router
from app.api.v1.templates import router as templates_router

# Root router to expose endpoints exactly as specified in the assignment spec
api_router = APIRouter()

api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(users_router, tags=["users"])
api_router.include_router(templates_router, tags=["templates"])
