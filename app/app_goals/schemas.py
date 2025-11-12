import enum
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.app_goals.models import GoalStatus


class GoalRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    target_days: int = Field(..., gt=0)
    start_date: date = Field(default_factory=date.today)


class GoalUpdate(BaseModel):
    end_date: Optional[date] = None
    status: Optional[GoalStatus] = None
    celery_task_ids: Optional[str] = None
    

class GoalResponse(BaseModel):
	id: UUID
	title: str
	description: Optional[str] = None
	start_date: date
	end_date: date
	status: GoalStatus
	target_days: int
