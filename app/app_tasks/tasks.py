from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import engine
from app_tasks.celery import celery
from app_goals.models import Goal
from app_goals.schemas import GoalUpdate
from app_goals.crud import get_active_goal, update_goal
from app_tasks.models import TaskDifficulty
from app_tasks.schemas import TaskCreate, TaskStatus
from app_tasks.crud import create_task, get_active_task, get_last_incomplete_task, update_task
from app_tasks.utils import remove_user_tasks
from app_reports.schemas import MonthlyReportRequest, WeeklyReportRequest
from app_reports.crud import create_monthly_report, create_weekly_report
from app_tasks.ai import generate_month_report, generate_next_task, generate_week_report


AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

def _today():
	return date.today()

@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def create_daily_task(self, user_id: UUID):
	async def run():
		async with AsyncSessionLocal() as db:
			goal: Goal = await get_active_goal(db, user_id)
			if not goal or goal.status != "active":
				return

			last_task = await get_active_task(db, goal.id)
			if last_task and last_task.status == TaskStatus.assigned:
				update_task(db, last_task, TaskStatus.missed)
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

			generated_task_data = generate_next_task(goal)
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
	import asyncio as _a; _a.run(run())


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def create_weekly_task(self, user_id: str):
	async def run():
		async with AsyncSessionLocal() as db:
			goal = await get_active_goal(db, user_id)
			if not goal:
				return
			data = generate_week_report(goal)
			payload = WeeklyReportRequest(
				goal_id=goal.id,
				week_start=data.get("week_start"),
				week_end=data.get("week_end"),
				completed_tasks=int(data.get("completed_tasks", 0)),
				missed_tasks=int(data.get("missed_tasks", 0)),
				ai_suggestion=data.get("ai_suggestion"),
			)
			await create_weekly_report(db, payload)
	import asyncio as _a; _a.run(run())


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def create_monthly_task(self, user_id: str):
	async def run():
		async with AsyncSessionLocal() as db:
			goal = await get_active_goal(db, user_id)
			if not goal:
				return
			data = generate_month_report(goal)
			payload = MonthlyReportRequest(
				goal_id=goal.id,
				month=int(data.get("month")),
				year=int(data.get("year")),
				completed_tasks=int(data.get("completed_tasks", 0)),
				missed_tasks=int(data.get("missed_tasks", 0)),
				summary=data.get("summary"),
				performance_score=float(data.get("performance_score")) if data.get("performance_score") is not None else None,
			)
			await create_monthly_report(db, payload)
	import asyncio as _a; _a.run(run())