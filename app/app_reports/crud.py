from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app_reports.models import WeeklyReport, MonthlyReport
from app_reports.schemas import WeeklyReportRequest, MonthlyReportRequest


async def create_weekly_report(db: AsyncSession, data: WeeklyReportRequest) -> WeeklyReport:
	report = WeeklyReport(
		goal_id=data.goal_id,
		week_start=data.week_start,
		week_end=data.week_end,
		completed_tasks=data.completed_tasks,
		missed_tasks=data.missed_tasks,
		ai_suggestion=data.ai_suggestion,
	)
	db.add(report)
	await db.commit()
	await db.refresh(report)
	return report


async def list_weekly_reports(db: AsyncSession, goal_id: UUID) -> list[WeeklyReport]:
    res = await db.execute(select(WeeklyReport).where(WeeklyReport.goal_id == goal_id))
    return res.scalars().all()


async def create_monthly_report(db: AsyncSession, data: MonthlyReportRequest

) -> MonthlyReport:
	report = MonthlyReport(
		goal_id=data.goal_id,
		month=data.month,
		year=data.year,
		summary=data.summary,
		performance_score=data.performance_score,
	)
	db.add(report)
	await db.commit()
	await db.refresh(report)
	return report


async def list_monthly_reports(db: AsyncSession, goal_id: UUID) -> list[MonthlyReport]:
    res = await db.execute(select(MonthlyReport).where(MonthlyReport.goal_id == goal_id))
    return res.scalars().all()