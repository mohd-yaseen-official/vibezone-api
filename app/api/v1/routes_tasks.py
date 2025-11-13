from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession


from app.app_users.crud import get_users_with_active_goal
from app.core.database import get_db
from app.core.deps import get_current_active_subscriber
from app.app_users.models import User
from app.app_users.schemas import MessageResponse
from app.app_goals.models import GoalStatus
from app.app_goals.schemas import GoalUpdate
from app.app_goals.crud import get_active_goal, get_goal, update_goal
from app.app_tasks.models import TaskStatus
from app.app_tasks.schemas import TaskResponse
from app.app_tasks.crud import create_daily_task_by_id, get_task, list_goal_tasks, update_task
from app.app_tasks.utils import remove_user_tasks


router = APIRouter()


@router.get("/", response_model=List[TaskResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_active_goal(db, current_user.id)
	if not goal:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_goal_tasks(db, goal.id)


@router.get("/{goal_id}", response_model=List[TaskResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_tasks_by_goal(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	goal = await get_goal(db, goal_id)
	if not goal and goal.user_id == current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
	return await list_goal_tasks(db, goal.id)


@router.patch("/status/{task_id}", response_model=MessageResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def update_task_status(task_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_subscriber)):
	task = await get_task(db, task_id)
	if not task or task.goal.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
	if not task.status == TaskStatus.assigned:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task already updated")
	
	await update_task(db, db_task=task, status=TaskStatus.done)
	if task.goal.end_date == datetime.today():
		await update_goal(db=db, db_goal=task.goal, goal_in=GoalUpdate(status=GoalStatus.completed))
		remove_user_tasks(task.goal.celery_task_ids)
	return MessageResponse(message="Task marked as done successfully")


@router.post("/create", response_model=MessageResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_daily_task(db: AsyncSession = Depends(get_db)):
	users = await get_users_with_active_goal(db)
	if users:
		for user in users:
			await create_daily_task_by_id(db=db, user_id=user.id)

	return MessageResponse(message=f"Daily tasks for {len(users)} users has been created successfully")