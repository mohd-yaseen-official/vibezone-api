from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from core.config import settings
from core.database import get_db
from core.security import create_access_token, verify_password
from core.deps import get_current_user
from lib.resend import send_reset_link

from app_users.models import User
from app_users.schemas import AuthRequest, ForgotPasswordRequest, GoogleLoginRequest, LoginResponse, MessageResponse, ResetPasswordRequest, UserResponse, PasswordResetTokenRequest
from app_users.crud import create_oauth_user, create_reset_token, create_user, delete_reset_tokens, get_reset_token_by_value, get_user_by_email, get_user_by_id, reset_password_action, soft_delete_user
from app_goals.crud import get_active_goal, soft_delete_goal
from app_tasks.utils import remove_user_tasks


router = APIRouter()


@router.post("/register", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def register(user_in: AuthRequest, db: AsyncSession = Depends(get_db)):
	existing = await get_user_by_email(db, user_in.email)
	if existing:
		raise HTTPException(status_code=400, detail="Email already registered")

	user = await create_user(db, user_in)
	return user


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def login(user_in: AuthRequest, db: AsyncSession = Depends(get_db)):
	user = await get_user_by_email(db, user_in.email)
	if not user or not user.password_hash or not verify_password(user_in.password, user.password_hash):
		raise HTTPException(status_code=400, detail="Invalid email or password")
	token = create_access_token(subject=user.email)

	return LoginResponse(token=token, user=user)

@router.post("/forgot-password", response_model=MessageResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
	email = payload.email
	if not email:
		raise HTTPException(status_code=400, detail="Email required")
	user = await get_user_by_email(db, email)
	if not user:
		raise HTTPException(status_code=404, detail="User not found")

	await delete_reset_tokens(db, user.id)

	token_value = create_access_token(subject=user.email, expires_minutes=settings.password_reset_expire_minutes)
	expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
	await create_reset_token(db, user.id, PasswordResetTokenRequest(token=token_value, expires_at=expires_at))

	background_tasks.add_task(send_reset_link, email, token_value)
	return MessageResponse(message="Email has been sent to your email")


@router.post("/reset-password", response_model=MessageResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
	token_value = payload.token
	new_password = payload.new_password
	if not token_value or not new_password:
		raise HTTPException(status_code=400, detail="Token and New Password required")

	token = await get_reset_token_by_value(db, token_value)
	if not token or token.used or token.expires_at < datetime.now(timezone.utc):
		raise HTTPException(status_code=400, detail="Invalid or expired token")

	user = await get_user_by_id(db, token.user_id)
	if not user:
		raise HTTPException(status_code=400, detail="User not found")

	if verify_password(new_password, user.password_hash):
		raise HTTPException(status_code=400, detail="Old Password and New Password cannot be same")

	await reset_password_action(db, user, token, new_password)
	return MessageResponse(message="Password has been reset successfully")


@router.get("/user", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_user(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
	return current_user


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT, response_model=None, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def delete_user(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
	await soft_delete_user(db, current_user)
	goal = await get_active_goal(db, current_user.id)
	if goal:
		remove_user_tasks(goal.celery_task_ids)
		await soft_delete_goal(db, goal)
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/google-login", response_model=LoginResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def google_login(google_token: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
	tok = google_token.token
	print(google_token)
	print(tok)
	if not tok:
		raise HTTPException(status_code=400, detail="Missing token")
	try:
		idinfo = id_token.verify_oauth2_token(tok, google_requests.Request(), settings.google_client_id)
		email = idinfo["email"]
		provider_id = idinfo["sub"]
	except Exception:
		raise HTTPException(status_code=400, detail="Invalid Google token")

	user = await get_user_by_email(db, email)
	if not user:
		user = await create_oauth_user(db, {
			"email": email,
			"provider_id": provider_id
		})

	token = create_access_token(subject=user.email)
	return LoginResponse(token=token, user=user)