"""Stripe API integration for multi-currency deposits and payouts."""

import os

import stripe

SUPPORTED_CURRENCIES = ["eur", "gbp", "usd"]

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def _configure():
    """Configure the Stripe SDK with the secret key."""
    stripe.api_key = STRIPE_SECRET_KEY


def create_payment_intent(amount_cents: int, currency: str, metadata: dict | None = None):
    """Create a Stripe PaymentIntent for a deposit.

    Args:
        amount_cents: Amount in the smallest currency unit (e.g. cents for USD/EUR/GBP).
        currency: ISO 4217 currency code (eur, gbp, usd).
        metadata: Optional metadata dict attached to the PaymentIntent.

    Returns:
        The created ``stripe.PaymentIntent`` object.

    Raises:
        ValueError: If the currency is not supported.
        stripe.error.StripeError: On Stripe API errors.
    """
    currency = currency.lower()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(
            f"Unsupported currency '{currency}'. Supported: {SUPPORTED_CURRENCIES}"
        )

    _configure()
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {},
        automatic_payment_methods={"enabled": True},
    )
    return intent


def create_payout(amount_cents: int, currency: str, description: str = "Portfolio payout"):
    """Create a Stripe Payout (withdrawal) in the specified currency.

    The payout is initiated from the platform Stripe balance to the
    connected bank account.

    Args:
        amount_cents: Amount in the smallest currency unit.
        currency: ISO 4217 currency code (eur, gbp, usd).
        description: Human-readable description shown in the Stripe Dashboard.

    Returns:
        The created ``stripe.Payout`` object.

    Raises:
        ValueError: If the currency is not supported.
        stripe.error.StripeError: On Stripe API errors.
    """
    currency = currency.lower()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(
            f"Unsupported currency '{currency}'. Supported: {SUPPORTED_CURRENCIES}"
        )

    _configure()
    payout = stripe.Payout.create(
        amount=amount_cents,
        currency=currency,
        description=description,
    )
    return payout


def construct_webhook_event(payload: bytes, sig_header: str):
    """Verify and construct a Stripe webhook Event.

    Args:
        payload: Raw request body bytes.
        sig_header: Value of the ``Stripe-Signature`` HTTP header.

    Returns:
        The verified ``stripe.Event`` object.

    Raises:
        stripe.error.SignatureVerificationError: If the signature is invalid.
    """
    _configure()
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
