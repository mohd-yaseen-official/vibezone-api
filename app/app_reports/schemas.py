from typing import Optional
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class WeeklyReportRequest(BaseModel):
	goal_id: UUID
	week_start: date
	week_end: date
	completed_tasks: int
	missed_tasks: int
	ai_suggestion: Optional[str] = None
	
	@field_validator('completed_tasks', 'missed_tasks')
	def validate_non_negative(cls, v):
		if v < 0:
			raise ValueError('Value cannot be negative')
		return v


class WeeklyReportResponse(BaseModel):
	id: UUID
	goal_id: UUID
	week_start: date
	week_end: date
	completed_tasks: int
	missed_tasks: int
	ai_suggestion: Optional[str]
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True


class MonthlyReportRequest(BaseModel):
	goal_id: UUID
	month: int
	year: int
	completed_tasks: int
	missed_tasks: int
	summary: Optional[str] = None
	performance_score: Optional[float] = None
	
	@field_validator('month')
	def validate_month(cls, v):
		if v < 1 or v > 12:
			raise ValueError('Month must be between 1 and 12')
		return v
	
	@field_validator('performance_score')
	def validate_performance_score(cls, v):
		if v is not None and (v < 0.00 or v > 100.00):
			raise ValueError('Performance score must be between 0.00 and 100.00')
		return v
	
	@field_validator('completed_tasks', 'missed_tasks')
	def validate_non_negative(cls, v):
		if v < 0:
			raise ValueError('Value cannot be negative')
		return v


class MonthlyReportResponse(BaseModel):
	id: UUID
	goal_id: UUID
	month: int
	year: int
	completed_tasks: int
	missed_tasks: int
	summary: Optional[str]
	performance_score: Optional[float]
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True

