import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_limiter.depends import RateLimiter
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

import stripe

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_subscriber, get_current_user
from app.app_users.models import User
from app.app_subscriptions.models import SubscriptionStatus
from app.app_subscriptions.schemas import (
    CheckoutSessionResponse, 
    SubscriptionStatusResponse, 
    SubscriptionCancelResponse,
    SubscriptionActionResponse,
    SubscriptionRequest
)
from app.app_subscriptions.crud import create_subscription, get_user_subscription, is_subscription_active, upsert_subscription_from_stripe


logger = logging.getLogger(__name__)

router = APIRouter()

def _extract_user_id(*objects) -> Optional[str]:
    for obj in objects:
        if not obj:
            continue
        metadata = obj.get("metadata", {})
        if metadata and metadata.get("user_id"):
            try:
                return metadata["user_id"]
            except (ValueError, TypeError):
                continue
    return None


@router.post('/create-checkout-session', response_model=CheckoutSessionResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
  
    try:
        db_subscription = await get_user_subscription(db, user.id)
        
        if not db_subscription:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)}
            )
            
            subscription_in = SubscriptionRequest(
                user_id=user.id,
                stripe_customer_id=customer.id,
                plan_id=settings.stripe_plan_id,
                status=SubscriptionStatus.created
            )
            
            db_subscription = await create_subscription(db, subscription_in)
        
        stripe_customer_id = db_subscription.stripe_customer_id
        
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": settings.stripe_plan_id, "quantity": 1}],
            mode="subscription",
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
            subscription_data={
                "metadata": {"user_id": str(user.id)}
            },
            allow_promotion_codes=True,
        )
        
        return CheckoutSessionResponse(url=session.url, id=session.id)
    
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(status_code=400, detail="Payment could not be processed. Please try again.")
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):        
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = settings.stripe_webhook_secret
    
    if not webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.type
    data = event.data.object
    
    logger.info(f"Processing Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            sub_id = data.get("subscription")
            
            if sub_id:
                stripe_sub = stripe.Subscription.retrieve(
                    sub_id,
                    expand=["items.data.price"]
                )
                
                user_id = _extract_user_id(stripe_sub, data)
                await upsert_subscription_from_stripe(db, stripe_sub, user_id=user_id)
                logger.info(f"Subscription created for user {user_id}")

        elif event_type == "customer.subscription.created":
            user_id = _extract_user_id(data)
            await upsert_subscription_from_stripe(db, data, user_id=user_id)
            logger.info(f"Subscription created: {data['id']}")

        elif event_type == "customer.subscription.updated":
            user_id = _extract_user_id(data)
            await upsert_subscription_from_stripe(db, data, user_id=user_id)
            logger.info(f"Subscription updated: {data['id']}")

        elif event_type == "customer.subscription.deleted":
            user_id = _extract_user_id(data)
            await upsert_subscription_from_stripe(db, data, user_id=user_id)
            logger.info(f"Subscription deleted: {data['id']}")

        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            sub_id = data.get("subscription")
            
            if sub_id:
                stripe_sub = stripe.Subscription.retrieve(
                    sub_id,
                    expand=["items.data.price"]
                )
                user_id = _extract_user_id(stripe_sub)
                await upsert_subscription_from_stripe(db, stripe_sub, user_id=user_id)
                logger.info(f"Invoice paid for subscription: {sub_id}")

        elif event_type == "invoice.payment_failed":
            sub_id = data.get("subscription")
            
            if sub_id:
                stripe_sub = stripe.Subscription.retrieve(
                    sub_id,
                    expand=["items.data.price"]
                )
                user_id = _extract_user_id(stripe_sub)
                await upsert_subscription_from_stripe(db, stripe_sub, user_id=user_id)
                logger.warning(f"Payment failed for subscription: {sub_id}")
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {str(e)}")
    return JSONResponse(status_code=200, content={"received": True})


@router.get("/subscription/status", response_model=SubscriptionStatusResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_subscription_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    subscription = await get_user_subscription(db, user.id)
    
    if not subscription:
        return SubscriptionStatusResponse(
            has_subscription=False,
            status=None,
            is_active=False,
            current_period_end=None,
            current_period_start=None,
            plan_id=None,
            price=None,
            cancel_at_period_end=False,
            trial_end=None
        )
    
    is_active = await is_subscription_active(subscription)
    
    return SubscriptionStatusResponse(
        has_subscription=True,
        status=subscription.status,
        is_active=is_active,
        current_period_end=subscription.current_period_end,
        current_period_start=subscription.current_period_start,
        plan_id=subscription.plan_id,
        price=float(subscription.price) if subscription.price else None,
        cancel_at_period_end=subscription.cancel_at_period_end or False,
        trial_end=subscription.trial_end
    )

@router.post("/subscription/cancel", response_model=SubscriptionCancelResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_subscriber)
):      
    subscription = await get_user_subscription(db, user.id)
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    try:
        stripe_sub = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        await upsert_subscription_from_stripe(db, stripe_sub, user_id=user.id)
        
        return SubscriptionCancelResponse(
            message="Subscription will be cancelled at the end of subscription end",
            cancel_at=subscription.current_period_end
        )
    
    except stripe.error.StripeError as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to cancel subscription")


@router.post("/subscription/reactivate", response_model=SubscriptionActionResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def reactivate_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_subscriber)
): 
    subscription = await get_user_subscription(db, user.id)
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    if subscription.current_period_end and subscription.current_period_end < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, 
            detail="Cannot reactivate subscription: current period has already ended"
        )

    try:
        stripe_sub = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        await upsert_subscription_from_stripe(db, stripe_sub, user_id=user.id)
        
        return SubscriptionActionResponse(
            message="Subscription reactivated successfully"
        )
    
    except stripe.error.StripeError as e:
        logger.error(f"Error reactivating subscription: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to reactivate subscription: {str(e)}")
