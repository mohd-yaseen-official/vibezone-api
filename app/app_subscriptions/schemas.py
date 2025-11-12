import enum
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app_subscriptions.models import SubscriptionStatus


class SubscriptionRequest(BaseModel):
    user_id: UUID
    stripe_customer_id: str
    plan_id: str
    status: SubscriptionStatus = SubscriptionStatus.created
    

class SubscriptionUpdate(BaseModel):
    stripe_subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    price: Optional[Decimal] = None
    subscription_metadata: Optional[str] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    

class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    stripe_customer_id: str
    stripe_subscription_id: Optional[str] = None
    plan_id: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    price: Optional[Decimal] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    

class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    status: Optional[str] = None
    is_active: bool = False
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    plan_id: Optional[str] = None
    price: Optional[Decimal] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CheckoutSessionResponse(BaseModel):
    url: str
    id: str


class SubscriptionCancelResponse(BaseModel):
    message: str
    cancel_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionActionResponse(BaseModel):
    message: str
    subscription: Optional[SubscriptionResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
