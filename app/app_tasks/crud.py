from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app_tasks.schemas import TaskCreate
from app_tasks.models import Task, TaskStatus


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
