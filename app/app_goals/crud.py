from datetime import timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.app_goals.models import Goal, GoalStatus
from app.app_goals.schemas import GoalRequest, GoalUpdate


def _calculate_end_date(start_date, target_days):
	return start_date + timedelta(days=max(0, target_days - 1))


async def create_new_goal(db: AsyncSession, user_id: str, goal_in: GoalRequest) -> Goal:
	end_date = _calculate_end_date(goal_in.start_date, goal_in.target_days)
	goal = Goal(
		user_id=user_id,
		title=goal_in.title,
		description=goal_in.description,
		target_days=goal_in.target_days,
		start_date=goal_in.start_date,
		end_date=end_date,
		status=GoalStatus.active,
	)
	
	db.add(goal)
	await db.commit()
	await db.refresh(goal)
	return goal


async def get_active_goal(db: AsyncSession, user_id: str) -> Optional[Goal]:
	res = await db.execute(select(Goal).where(Goal.user_id == user_id, Goal.status == GoalStatus.active))
	return res.scalars().first()


async def get_goals(db: AsyncSession, user_id: str, include_deleted: bool = False) -> List[Goal]:
	goals = select(Goal).where(Goal.user_id == user_id)
	if not include_deleted:
		goals = goals.where(Goal.status != GoalStatus.deleted)
	goals = goals.order_by(Goal.start_date.desc())
	res = await db.execute(goals)
	
	return res.scalars().all()


async def get_goal(db: AsyncSession, goal_id: str) -> Optional[Goal]:
	res = await db.execute(select(Goal).where(Goal.id == goal_id))
	return res.scalars().first()


async def update_goal(db: AsyncSession, db_goal: Goal, goal_in: GoalUpdate) -> Optional[Goal]:
	goal_data = goal_in.model_dump(exclude_unset=True)

	if goal_data:
		for field, value in goal_data.items():
			setattr(db_goal, field, value)

		db.add(db_goal)
		await db.commit()
		await db.refresh(db_goal)

	return db_goal


async def soft_delete_goal(db: AsyncSession, db_goal: Goal) -> Goal:
	db_goal.status = GoalStatus.deleted
	db.add(db_goal)
	await db.commit()
	await db.refresh(db_goal)
	return db_goal
