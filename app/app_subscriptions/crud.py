
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from app_subscriptions.models import StripeSubscription, SubscriptionStatus
from app_subscriptions.schemas import SubscriptionRequest, SubscriptionUpdate
from app_users.models import User


logger = logging.getLogger(__name__)


def _convert_timestamp(timestamp) -> Optional[datetime]:
    if timestamp:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return None


async def get_subscription_by_id(db: AsyncSession, subscription_id: UUID) -> Optional[StripeSubscription]:
    subscriptions = await db.execute(select(StripeSubscription).where(StripeSubscription.id == subscription_id))
    return subscriptions.scalars().first()


async def get_user_subscription(db: AsyncSession, user_id: UUID) -> Optional[StripeSubscription]:
    subscriptions = await db.execute(
        select(StripeSubscription).where(StripeSubscription.user_id == user_id).order_by(StripeSubscription.created_at.desc())
    )
    return subscriptions.scalars().first()


async def get_subscription_by_stripe_id(db: AsyncSession, stripe_subscription_id: str) -> Optional[StripeSubscription]:
    subscriptions = await db.execute(
        select(StripeSubscription).where(StripeSubscription.stripe_subscription_id == stripe_subscription_id)
    )
    return subscriptions.scalars().first()


async def create_subscription(db: AsyncSession, subscription_in: SubscriptionRequest) -> StripeSubscription:
    subscription = StripeSubscription(**subscription_in.model_dump())
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def update_subscription(
    db: AsyncSession, 
    db_subscription: StripeSubscription, 
    subscription_in: SubscriptionUpdate
) -> StripeSubscription:
    update_dict = subscription_in.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None or key in ['stripe_subscription_id', 'status']:
            setattr(db_subscription, key, value)
    
    db.add(db_subscription)
    await db.commit()
    await db.refresh(db_subscription)
    return db_subscription


async def upsert_subscription_from_stripe(
    db: AsyncSession,
    stripe_sub: dict,
    user_id: UUID | None = None
) -> Optional[StripeSubscription]:
    stripe_subscription_id = stripe_sub.id
    stripe_customer_id = stripe_sub.get("customer")
    
    plan_id = settings.stripe_plan_id
    items = stripe_sub.get("items", {}).get("data", [])
    if items:
        plan_id = items[0].get("price", {}).get("id") or plan_id
    
    status = stripe_sub.get("status")
    current_period_end = _convert_timestamp(stripe_sub.get("current_period_end"))
    current_period_start = _convert_timestamp(stripe_sub.get("current_period_start"))
    
    canceled_at = _convert_timestamp(stripe_sub.get("canceled_at"))
    cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    
    trial_start = _convert_timestamp(stripe_sub.get("trial_start"))
    trial_end = _convert_timestamp(stripe_sub.get("trial_end"))
    
    price = None
    if items and items[0].get("price", {}).get("unit_amount"):
        price = items[0].get("price").get("unit_amount") / 100.0
    
    subscription_metadata = json.dumps(stripe_sub.get("metadata", {}))
    
    if not user_id:
        sub_metadata = stripe_sub.get("metadata", {})
        if sub_metadata and sub_metadata.get("user_id"):
            try:
                user_id = UUID(sub_metadata["user_id"])
            except (ValueError, TypeError):
                pass
    
    db_subscription = await get_subscription_by_stripe_id(db, stripe_subscription_id)
    
    if not db_subscription:
        if not user_id:
            logger.error(
                f"Cannot create subscription {stripe_subscription_id} without user_id"
            )
            return None
        
        create_data = SubscriptionRequest(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            plan_id=plan_id,
            status=SubscriptionStatus[status if status else "active"]
        )
        db_subscription = await create_subscription(db, create_data)
        logger.info(f"Created subscription {stripe_subscription_id} for user {user_id}")
    
    subscription_in = SubscriptionUpdate(
        stripe_subscription_id,
        plan_id,
        status,
        current_period_end,
        current_period_start,
        canceled_at,
        cancel_at_period_end,
        price,
        subscription_metadata,
        trial_start,
        trial_end,
    )
    db_subscription = await update_subscription(db, db_subscription, subscription_in)
    logger.info(f"Updated subscription {stripe_subscription_id} for user {user_id}")
    
    return db_subscription

async def is_subscription_active(db_subscription: Optional[StripeSubscription]) -> bool:
    if not db_subscription:
        return False
    
    valid_statuses = ["active", "trialing"]
    
    if db_subscription.status not in valid_statuses:
        return False
    
    if db_subscription.current_period_end:
        return db_subscription.current_period_end > datetime.now(timezone.utc)
    
    return True
