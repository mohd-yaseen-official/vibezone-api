from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_active_subscriber
from app_users.models import User
from app_goals.crud import get_active_goal
from app_reports.schemas import MonthlyReportResponse, WeeklyReportResponse
from app_reports.crud import list_monthly_reports, list_weekly_reports


router = APIRouter()

@router.get("/weekly-report", response_model=List[WeeklyReportResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_weekly_reports_route(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_active_goal(db, current_user.id)
	if not goal:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_weekly_reports(db, goal.id)


@router.get("/monthly-report", response_model=List[MonthlyReportResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_monthly_reports_route(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_active_goal(db, current_user.id)
	if not goal:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_monthly_reports(db, goal.id)
