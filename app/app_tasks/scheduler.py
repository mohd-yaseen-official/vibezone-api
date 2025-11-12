from datetime import datetime, timedelta, timezone

from app_tasks.celery import celery
from app_tasks.tasks import create_daily_task, create_monthly_task, create_weekly_task


def schedule_user_task(user_id: str, start_time: datetime = None):
	if start_time is None:
		start_time = datetime.now(timezone.utc)

	first_daily = start_time.replace(hour=5, minute=0, second=0, microsecond=0)
	while first_daily < datetime.now(timezone.utc):
		first_daily += timedelta(days=1)
	daily_task = create_daily_task.apply_async(args=[user_id], eta=first_daily)

	weekly_task_eta = start_time + timedelta(days=7)
	weekly_task = create_weekly_task.apply_async(args=[user_id], eta=weekly_task_eta)

	monthly_task_eta = start_time + timedelta(days=30)
	monthly_task = create_monthly_task.apply_async(args=[user_id], eta=monthly_task_eta)

	return f"{daily_task.id},{weekly_task.id},{monthly_task.id}"
