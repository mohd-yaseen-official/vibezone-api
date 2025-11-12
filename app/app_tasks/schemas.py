import enum
from typing import Optional
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app_tasks.models import TaskDifficulty, TaskStatus


class TaskCreate(BaseModel):
	goal_id: UUID
	title: str = Field(..., max_length=255)
	description: Optional[str] = None
	assigned_date: date
	status: TaskStatus = TaskStatus.assigned
	difficulty: TaskDifficulty = TaskDifficulty.medium
	ai_generated: bool = True


class TaskResponse(BaseModel):
	id: UUID
	goal_id: UUID
	title: str
	description: Optional[str]
	assigned_date: date
	status: TaskStatus
	difficulty: TaskDifficulty
	ai_generated: bool

	class Config:
		from_attributes = True

