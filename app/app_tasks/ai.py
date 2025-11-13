import json
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from google import genai

from app.core.config import settings
from app.core.database import get_db
from app.app_tasks.utils import create_monthly_report_prompt, create_next_task_prompt, create_weekly_report_prompt
from app.app_tasks.models import Task


client = genai.Client(api_key=settings.gemini_api_key)

async def generate_next_task(db: AsyncSession, goal):
	tasks_raw = await db.execute(select(Task).where(Task.goal_id == goal.id))
	tasks = tasks_raw.scalars().all()
	prompts = create_next_task_prompt(goal, tasks)
	resp = client.models.generate_content(
		model=settings.ai_model,
		contents=[{"role": "user", "parts": [{"text": f"{prompts['system']}\n\nUser: {prompts['user']}"}]}]
	)
	return json.loads(resp.text)


async def generate_week_report(goal, db: AsyncSession = get_db()):
	now = datetime.now()
	tasks = db.execute(select(Task).where(and_(
        Task.date >= now - timedelta(days=7),
        Task.date <= now
    )))

	prompts = create_weekly_report_prompt(goal, tasks)
	resp = client.models.generate_content(
		model=settings.ai_model,
		contents=[{"role": "user", "parts": [{"text": f"{prompts['system']}\n\nUser: {prompts['user']}"}]}]
	)
	return json.loads(resp.text)


async def generate_month_report(goal, db: AsyncSession = get_db()):
	now = datetime.now()
	tasks = db.execute(select(Task).where(and_(
        Task.date >= now - timedelta(days=30),
        Task.date <= now
    )))

	prompts = create_monthly_report_prompt(goal, tasks)
	resp = client.models.generate_content(
		model=settings.ai_model,
		contents=[{"role": "user", "parts": [{"text": f"{prompts['system']}\n\nUser: {prompts['user']}"}]}]
	)
	return json.loads(resp.text)