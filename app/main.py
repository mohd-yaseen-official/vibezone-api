from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from redis.asyncio import from_url as redis_from_url
import stripe

from core.config import settings
from api.v1.routes_auth import router as auth_router
from api.v1.routes_goals import router as goals_router
from api.v1.routes_tasks import router as tasks_router
from api.v1.routes_reports import router as reports_router
from api.v1.routes_subscriptions import router as subscriptions_router


stripe.api_key = settings.stripe_secret_key

app = FastAPI(title=settings.project_name, version=settings.version)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
	redis = redis_from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
	await FastAPILimiter.init(redis)


app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"]) 
app.include_router(goals_router, prefix="/api/v1/goals", tags=["goals"]) 
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(subscriptions_router, prefix="/api/v1/subscriptions", tags=["subscriptions"]) 
