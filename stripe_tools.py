"""
stripe_tools.py — Real Stripe API integration
Replaces the mock get_payment_info() function in main.py

Usage:
    from stripe_tools import get_stripe_payment_info
"""

import os
import stripe
from datetime import datetime, timezone

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


async def get_stripe_payment_info(email: str) -> dict:
    """
    Fetch real payment info from Stripe for a given customer email.
    Returns a structured dict ready to be passed to the LLM.
    """
    result = {
        "found": False,
        "email": email,
        "customer_id": None,
        "plan": None,
        "subscription_status": None,
        "current_period_end": None,
        "default_payment_method": None,
        "card_brand": None,
        "card_last4": None,
        "card_exp_month": None,
        "card_exp_year": None,
        "failed_payment_attempts": 0,
        "last_payment_status": None,
        "last_payment_amount": None,
        "last_payment_date": None,
        "last_payment_error": None,
        "recent_invoices": [],
    }

    try:
        # ── 1. Find the Stripe customer by email ──────────────────────────────
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            result["error"] = f"No Stripe customer found for {email}"
            return result

        customer = customers.data[0]
        result["found"] = True
        result["customer_id"] = customer.id

        # ── 2. Get active subscription ────────────────────────────────────────
        subscriptions = stripe.Subscription.list(
            customer=customer.id,
            status="all",
            limit=1,
            expand=["data.default_payment_method"],
        )

        if subscriptions.data:
            sub = subscriptions.data[0]
            result["subscription_status"] = sub.status
            result["failed_payment_attempts"] = sub.latest_invoice.attempt_count if hasattr(sub, 'latest_invoice') else 0

            # Plan name
            if sub.items.data:
                price = sub.items.data[0].price
                result["plan"] = (
                    f"{price.nickname or price.id} — "
                    f"${price.unit_amount / 100:.2f}/{price.recurring.interval}"
                )

            # Period end
            result["current_period_end"] = datetime.fromtimestamp(
                sub.current_period_end, tz=timezone.utc
            ).isoformat()

            # Payment method
            pm = sub.default_payment_method
            if pm and pm.card:
                result["card_brand"] = pm.card.brand
                result["card_last4"] = pm.card.last4
                result["card_exp_month"] = pm.card.exp_month
                result["card_exp_year"] = pm.card.exp_year
                result["default_payment_method"] = f"{pm.card.brand} •••• {pm.card.last4}"

        # ── 3. Get recent invoices (last 5) ───────────────────────────────────
        invoices = stripe.Invoice.list(customer=customer.id, limit=5)
        recent_invoices = []

        for inv in invoices.data:
            invoice_data = {
                "id": inv.id,
                "status": inv.status,
                "amount": f"${inv.amount_due / 100:.2f}",
                "date": datetime.fromtimestamp(inv.created, tz=timezone.utc).isoformat(),
                "error": None,
            }

            # Capture payment error reason
            if inv.last_finalization_error:
                invoice_data["error"] = inv.last_finalization_error.message
            if hasattr(inv, "payment_intent") and inv.payment_intent:
                pi = stripe.PaymentIntent.retrieve(inv.payment_intent)
                if pi.last_payment_error:
                    invoice_data["error"] = pi.last_payment_error.message
                    invoice_data["error_code"] = pi.last_payment_error.code

            recent_invoices.append(invoice_data)

        result["recent_invoices"] = recent_invoices

        # Set latest payment summary
        if recent_invoices:
            latest = recent_invoices[0]
            result["last_payment_status"] = latest["status"]
            result["last_payment_amount"] = latest["amount"]
            result["last_payment_date"] = latest["date"]
            result["last_payment_error"] = latest.get("error")

    except stripe.error.AuthenticationError:
        result["error"] = "Invalid Stripe API key. Check STRIPE_SECRET_KEY in .env"
    except stripe.error.StripeError as e:
        result["error"] = f"Stripe API error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    return result
