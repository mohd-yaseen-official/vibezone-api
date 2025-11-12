import enum

from sqlalchemy import Column, String, Text, Integer, Date, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base
from common.mixins import IDMixin


class GoalStatus(str, enum.Enum):
	active = "active"
	completed = "completed"
	deleted = "deleted"

class Goal(Base, IDMixin):
	__tablename__ = "goals"

	user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	title = Column(String(255), nullable=False)
	description = Column(Text, nullable=True)
	start_date = Column(Date, nullable=False)
	end_date = Column(Date, nullable=True)
	status = Column(SQLEnum(GoalStatus), nullable=False, default=GoalStatus.active)
	target_days = Column(Integer, nullable=False)
	celery_task_ids = Column(Text, nullable=True)

	user = relationship("User", back_populates="goals", lazy="selectin")
	tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan", lazy="selectin")
	weekly_reports = relationship("WeeklyReport", back_populates="goal", cascade="all, delete-orphan", lazy="selectin")
	monthly_reports = relationship("MonthlyReport", back_populates="goal", cascade="all, delete-orphan", lazy="selectin")
