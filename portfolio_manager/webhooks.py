"""Stripe webhook handlers for the portfolio manager."""

import logging

import stripe

from stripe_integration import construct_webhook_event
from transactions import update_transaction_status

logger = logging.getLogger(__name__)


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Process an incoming Stripe webhook event.

    Supported event types:
    - ``payment_intent.succeeded`` – marks the matching deposit as *completed*.
    - ``payout.paid`` – marks the matching payout as *completed*.

    Args:
        payload: Raw HTTP request body.
        sig_header: Value of the ``Stripe-Signature`` header.

    Returns:
        A dict with ``{"status": "handled", "event_type": <type>}`` on success,
        or ``{"status": "ignored", "event_type": <type>}`` for unhandled events.

    Raises:
        stripe.error.SignatureVerificationError: If the webhook signature check fails.
    """
    event = construct_webhook_event(payload, sig_header)
    event_type = event["type"]

    if event_type == "payment_intent.succeeded":
        intent = event["data"]["object"]
        _handle_payment_intent_succeeded(intent)
        return {"status": "handled", "event_type": event_type}

    if event_type == "payout.paid":
        payout = event["data"]["object"]
        _handle_payout_paid(payout)
        return {"status": "handled", "event_type": event_type}

    logger.debug("Unhandled webhook event type: %s", event_type)
    return {"status": "ignored", "event_type": event_type}


# ── Private helpers ────────────────────────────────────────────────────────


def _handle_payment_intent_succeeded(intent: dict) -> None:
    """Update deposit transaction status to 'completed'."""
    stripe_id = intent.get("id", "")
    currency = intent.get("currency", "")
    amount_cents = intent.get("amount_received", intent.get("amount", 0))
    amount = amount_cents / 100.0

    update_transaction_status(stripe_id, "completed")
    logger.info(
        "PaymentIntent succeeded: id=%s currency=%s amount=%s",
        stripe_id,
        currency,
        amount,
    )


def _handle_payout_paid(payout: dict) -> None:
    """Update payout transaction status to 'completed'."""
    stripe_id = payout.get("id", "")
    currency = payout.get("currency", "")
    amount_cents = payout.get("amount", 0)
    amount = amount_cents / 100.0

    update_transaction_status(stripe_id, "completed")
    logger.info(
        "Payout paid: id=%s currency=%s amount=%s",
        stripe_id,
        currency,
        amount,
    )
