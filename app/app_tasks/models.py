import enum

from sqlalchemy import Column, String, Text, Boolean, Date, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.common.mixins import IDMixin


class TaskStatus(str, enum.Enum):
	assigned = "assigned"
	done = "done"
	missed = "missed"

class TaskDifficulty(str, enum.Enum):
	easy = "easy"
	medium = "medium"
	hard = "hard"

class Task(Base, IDMixin):
	__tablename__ = "tasks"

	goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
	title = Column(String(255), nullable=False)
	description = Column(Text, nullable=True)
	assigned_date = Column(Date, nullable=False)
	status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.assigned, index=True)
	difficulty = Column(SQLEnum(TaskDifficulty), nullable=False, default=TaskDifficulty.medium)
	ai_generated = Column(Boolean, nullable=False, default=True)

	goal = relationship("Goal", back_populates="tasks", lazy="selectin")
