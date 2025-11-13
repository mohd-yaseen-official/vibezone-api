from datetime import date, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.app_tasks.ai import generate_next_task
from app.app_goals.models import Goal
from app.app_goals.schemas import GoalUpdate
from app.app_goals.crud import get_active_goal, update_goal
from app.app_tasks.schemas import TaskCreate
from app.app_tasks.models import Task, TaskDifficulty, TaskStatus


async def create_task(db: AsyncSession, task_in: TaskCreate) -> Task:
	task = Task(
		goal_id=task_in.goal_id,
		title=task_in.title,
		description=task_in.description,
		assigned_date=task_in.assigned_date,
		status=task_in.status,
		difficulty=task_in.difficulty,
		ai_generated=task_in.ai_generated,
	)
	db.add(task)
	await db.commit()
	await db.refresh(task)
	return task


async def list_goal_tasks(db: AsyncSession, goal_id: UUID) -> List[Task]:
	res = await db.execute(select(Task).where(Task.goal_id == goal_id))
	return res.scalars().all()


async def get_task(db: AsyncSession, task_id: UUID) -> Optional[Task]:
	res = await db.execute(select(Task).where(Task.id == task_id))
	return res.scalars().first()


async def get_last_incomplete_task(db: AsyncSession, goal_id: UUID) -> Optional[Task]:
	res = await db.execute(
		select(Task)
		.where(Task.goal_id == goal_id)
		.order_by(desc(Task.assigned_date))
		.limit(1)
	)
	return res.scalars().first()


async def get_active_task(db: AsyncSession, goal_id: UUID) -> Optional[Task]:
	res = await db.execute(
		select(Task)
		.where(Task.goal_id == goal_id)
		.order_by(desc(Task.assigned_date))
		.limit(1)
	)
	return res.scalars().first()


async def update_task(db: AsyncSession, db_task: Task, status: TaskStatus) -> Task:
	if status is not None:
		db_task.status = status
	
	db.add(db_task)
	await db.commit()
	await db.refresh(db_task)
	return db_task


###
def _today():
	return date.today()


async def create_daily_task_by_id(db: AsyncSession, user_id: UUID):
	goal: Goal = await get_active_goal(db, user_id)
	if not goal or goal.status != "active":
		return

	last_task = await get_active_task(db, goal.id)
	if last_task and last_task.status == TaskStatus.assigned:
		await update_task(db, last_task, TaskStatus.missed)
		new_task = TaskCreate(
			title=last_task.title,
			description=last_task.description,
			assigned_date=_today(),
			difficulty=last_task.difficulty,
			status=TaskStatus.assigned,
			ai_generated=last_task.ai_generated,
			goal_id=goal.id,
		)
		await create_task(db, new_task)

		end_date = (goal.end_date or _today()) + timedelta(days=1)
		
		await update_goal(db, db_goal=goal, goal_in=GoalUpdate(end_date=end_date))
		return

	generated_task_data = await generate_next_task(db, goal)
	payload = TaskCreate(
		title=generated_task_data.get("title"),
		description=generated_task_data.get("description"),
		assigned_date=_today(),
		due_date=generated_task_data.get("due_date"),
		difficulty=TaskDifficulty(generated_task_data.get("difficulty", "medium")),
		status=TaskStatus(generated_task_data.get("status", "assigned")),
		ai_generated=True,
		goal_id=goal.id,
	)
	
	return await create_task(db, payload)