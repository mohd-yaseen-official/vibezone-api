from uuid import UUID

from sqlalchemy import Column, Integer, Date, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base
from common.mixins import CreatedUpdatedAtMixin, IDMixin


class WeeklyReport(Base, IDMixin, CreatedUpdatedAtMixin):
	__tablename__ = "weekly_reports"

	goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
	week_start = Column(Date, nullable=False)
	week_end = Column(Date, nullable=False)
	completed_tasks = Column(Integer, nullable=False, default=0)
	missed_tasks = Column(Integer, nullable=False, default=0)
	ai_suggestion = Column(Text, nullable=True)

	goal = relationship("Goal", back_populates="weekly_reports", lazy="selectin")


class MonthlyReport(Base, IDMixin, CreatedUpdatedAtMixin):
	__tablename__ = "monthly_reports"

	goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
	month = Column(Integer, nullable=False)
	year = Column(Integer, nullable=False)
	completed_tasks = Column(Integer, nullable=False, default=0)
	missed_tasks = Column(Integer, nullable=False, default=0)
	summary = Column(Text, nullable=True)
	performance_score = Column(Numeric(5, 2), nullable=True)

	goal = relationship("Goal", back_populates="monthly_reports", lazy="selectin")
