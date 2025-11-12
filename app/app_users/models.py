import enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.common.mixins import IDMixin, CreatedUpdatedAtMixin


class AuthProvider(str, enum.Enum):
	email = "email"
	google = "google"
      
class User(Base, IDMixin, CreatedUpdatedAtMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    provider = Column(SQLEnum(AuthProvider), nullable=False, default=AuthProvider.email)
    provider_id = Column(Text, nullable=True)
    
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    subscriptions = relationship("StripeSubscription", back_populates="user", cascade="all, delete-orphan", lazy="selectin")


class PasswordResetToken(Base, IDMixin, CreatedUpdatedAtMixin):
	__tablename__ = "password_reset_tokens"

	user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	token = Column(String, unique=True, nullable=False, index=True)
	expires_at = Column(DateTime(timezone=True), nullable=False)
	used = Column(Boolean, nullable=False, default=False)

	user = relationship("User", back_populates="password_reset_tokens", lazy="selectin")