from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.app_users.models import User
from app.app_users.crud import get_user_by_email
from app.app_subscriptions.crud import get_user_subscription


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
	token: str = Depends(oauth2_scheme),
	db: AsyncSession = Depends(get_db)
) -> User:
	email = decode_token(token)
	if not email:
		raise HTTPException(status_code=401, detail="Invalid token")
	user = await get_user_by_email(db, email)
	if not user:
		raise HTTPException(status_code=401, detail="User not found")
	return user


async def get_current_active_subscriber(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user)
) -> User:
	try:
		await get_user_subscription(db, current_user.id)
		return current_user
	except Exception:
		raise HTTPException(
			status_code=403, 
			detail="Active subscription required to access this feature"
		)