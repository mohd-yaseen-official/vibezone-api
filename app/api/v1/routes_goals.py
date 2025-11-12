from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_active_subscriber
from app_users.models import User
from app_goals.crud import create_new_goal, get_active_goal, get_goal, get_goals, soft_delete_goal, update_goal
from app_goals.schemas import GoalRequest, GoalResponse, GoalStatus, GoalUpdate
from app_tasks.schemas import TaskResponse
from app_tasks.crud import list_goal_tasks
from app_tasks.scheduler import schedule_user_task
from app_tasks.utils import remove_user_tasks
from app_reports.schemas import MonthlyReportResponse, WeeklyReportResponse
from app_reports.crud import list_monthly_reports, list_weekly_reports


router = APIRouter()

@router.post("/create", response_model=GoalResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_goal(data: GoalRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	existing = await get_active_goal(db, current_user.id)
	if existing:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has an active goal")
	goal = await create_new_goal(db, user_id=current_user.id, goal_in=data)
	
	try:
		task_ids = schedule_user_task(current_user.id)
	except:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occured during task scheduling")
	
	await update_goal(db, db_goal=goal, goal_in=GoalUpdate(celery_task_ids=task_ids))
	return goal


@router.get("/", response_model=List[GoalResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_goals(include_deleted: bool = Query(True), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	return await get_goals(db, user_id=current_user.id, include_deleted=include_deleted)


@router.get("/{goal_id}", response_model=GoalResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_individual_goal(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal or goal.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def delete_goal(goal_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal or goal.user_id != current_user.id or goal.status == GoalStatus.deleted:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	if getattr(goal, "celery_task_ids", None):
		remove_user_tasks(goal.celery_task_ids)
	await soft_delete_goal(db, db_goal=goal)
	return None


@router.get("/{goal_id}/tasks", response_model=List[TaskResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_goal_tasks(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal or goal.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_goal_tasks(db, goal.id)


@router.get("/{goal_id}/reports/weekly", response_model=List[WeeklyReportResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_goal_weekly_reports(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal or goal.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_weekly_reports(db, goal.id)


@router.get("/{goal_id}/reports/monthly", response_model=List[MonthlyReportResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_goal_monthly_reports(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal or goal.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_monthly_reports(db, goal.id)