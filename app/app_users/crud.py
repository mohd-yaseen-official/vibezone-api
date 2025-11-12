from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.app_users.models import PasswordResetToken, User
from app.app_users.schemas import AuthRequest, OAuthRequest, PasswordResetTokenRequest


async def create_user(db: AsyncSession, user_in: AuthRequest) -> User:
	user = User(
		email=user_in.email,
		password_hash=hash_password(user_in.password)
	)
	db.add(user)
	await db.commit()
	await db.refresh(user)
	return user


async def create_oauth_user(db: AsyncSession, user_in: OAuthRequest) -> User:
	user = User(
		email=user_in.email,
		provider=user_in.provider,
        provider_id=user_in.provider_id
	)
	db.add(user)
	await db.commit()
	await db.refresh(user)
	return user
    

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    users = await db.execute(select(User).where(User.email == email, User.is_active == True))
    return users.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    users = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    return users.scalars().first()


async def soft_delete_user(db: AsyncSession, db_user: User) -> None:
	db_user.is_active = False
	db.add(db_user)
	await db.commit()
	await db.refresh(db_user)
	return None


async def create_reset_token(db: AsyncSession, user_id: UUID, password_reset_token_in: PasswordResetTokenRequest) -> PasswordResetToken:
	reset_token = PasswordResetToken(
		user_id=user_id, 
		token=password_reset_token_in.token,
		expires_at=password_reset_token_in.expires_at
	)
	db.add(reset_token)
	await db.commit()
	await db.refresh(reset_token)
	return reset_token


async def get_reset_token_by_value(db: AsyncSession, token_value: str) -> Optional[PasswordResetToken]:
    reset_tokens = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token_value))
    return reset_tokens.scalars().first()


async def delete_reset_tokens(db: AsyncSession, user_id: UUID) :
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
    

async def reset_password_action(db: AsyncSession, db_user: User, db_token: PasswordResetToken, new_password: str):
	db_user.password_hash = hash_password(new_password)
	db_token.used = True
	await db.commit()