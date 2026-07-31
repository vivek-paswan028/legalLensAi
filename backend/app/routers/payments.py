import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_from_cookie as get_current_user
from app.models.db_models import User, AuditLog
from app.config import settings

log = logging.getLogger("legallens")
router = APIRouter()

try:
    import stripe
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout Session for Professional tier subscription ($49/mo)."""
    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    except Exception:
        body = {}
    plan_tier = body.get("tier", "pro")

    if not settings.STRIPE_SECRET_KEY or stripe is None:
        # Demo / Test mode fallback when no Stripe API key is provided
        user.tier = "pro"
        db.commit()

        audit = AuditLog(
            user_id=user.id,
            action="stripe_checkout_demo",
            resource_type="user",
            resource_id=user.id,
            details={"tier": "pro", "mode": "demo"},
        )
        db.add(audit)
        db.commit()

        log.info("stripe.demo_checkout", extra={"user_id": user.id, "tier": "pro"})
        return {"url": "/dashboard?payment=success&mode=demo"}

    try:
        # Real Stripe Checkout Session creation
        domain_url = settings.FRONTEND_URL.rstrip("/")
        line_items = []

        if settings.STRIPE_PRICE_ID_PRO:
            line_items.append({
                "price": settings.STRIPE_PRICE_ID_PRO,
                "quantity": 1,
            })
        else:
            # Dynamic price creation for $49/mo if price ID not set
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "LegalLens AI Professional Plan",
                        "description": "250 contract reviews/month, full risk analysis, smart redlining, and priority support.",
                    },
                    "unit_amount": 4900,  # $49.00 USD
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            })

        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            client_reference_id=user.id,
            payment_method_types=["card"],
            line_items=line_items,
            mode="subscription",
            success_url=f"{domain_url}/dashboard?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain_url}/dashboard?payment=cancelled",
            metadata={
                "user_id": user.id,
                "tier": plan_tier,
            }
        )

        audit = AuditLog(
            user_id=user.id,
            action="stripe_checkout_start",
            resource_type="user",
            resource_id=user.id,
            details={"session_id": checkout_session.id},
        )
        db.add(audit)
        db.commit()

        return {"url": checkout_session.url}

    except Exception as e:
        log.error("stripe.checkout_failed", extra={"error": str(e), "user_id": user.id})
        raise HTTPException(status_code=500, detail=f"Stripe payment error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    """Stripe Webhook endpoint for processing async payment events."""
    payload = await request.body()

    if not settings.STRIPE_WEBHOOK_SECRET or stripe is None:
        return {"status": "ignored", "reason": "Webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")

        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.tier = "pro"
                db.commit()
                log.info("stripe.subscription_activated", extra={"user_id": user.id})

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        # Handle cancellation
        log.info("stripe.subscription_canceled", extra={"customer_id": customer_id})

    return {"status": "success"}


@router.get("/portal")
async def get_customer_portal(user: User = Depends(get_current_user)):
    """Generate Stripe Customer Portal link to manage subscription."""
    if not settings.STRIPE_SECRET_KEY or stripe is None:
        return {"url": "/dashboard?mode=demo"}

    try:
        domain_url = settings.FRONTEND_URL.rstrip("/")
        # Search for customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if customers and customers.data:
            portal_session = stripe.billing_portal.Session.create(
                customer=customers.data[0].id,
                return_url=f"{domain_url}/dashboard",
            )
            return {"url": portal_session.url}
        else:
            return {"url": f"{domain_url}/dashboard"}
    except Exception as e:
        log.error("stripe.portal_failed", extra={"error": str(e)})
        return {"url": f"{domain_url}/dashboard"}
