import json
import logging
import os
import sys

import requests
import stripe
from flask import Flask, jsonify, render_template, request

# Allow sibling modules to be imported when the app is run directly.
sys.path.insert(0, os.path.dirname(__file__))

import stripe_integration  # noqa: E402
import transactions as tx_store  # noqa: E402
import webhooks  # noqa: E402

logger = logging.getLogger(__name__)

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "portfolio_data.json")

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"


def load_portfolio():
    """Load portfolio data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"tokens": []}
    with open(DATA_FILE) as f:
        return json.load(f)


def save_portfolio(data):
    """Save portfolio data to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def fetch_token_price(token_id):
    """Fetch current token price from CoinGecko API."""
    try:
        response = requests.get(
            COINGECKO_API_URL,
            params={"ids": token_id, "vs_currencies": "usd"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if token_id in data:
            return data[token_id].get("usd")
    except requests.RequestException:
        pass
    return None


@app.route("/")
def index():
    """Render the portfolio manager web form."""
    return render_template("portfolio.html")


@app.route("/portfolio", methods=["GET"])
def get_portfolio():
    """Return the current portfolio with live prices."""
    portfolio = load_portfolio()
    tokens = portfolio.get("tokens", [])

    enriched = []
    total_value = 0.0

    for token in tokens:
        price = fetch_token_price(token.get("id", ""))
        amount = token.get("amount", 0)
        value = price * amount if price is not None else None
        if value is not None:
            total_value += value
        enriched.append(
            {
                "address": token.get("address", ""),
                "id": token.get("id", ""),
                "name": token.get("name", ""),
                "amount": amount,
                "price_usd": price,
                "value_usd": value,
            }
        )

    return jsonify({"tokens": enriched, "total_value_usd": total_value})


@app.route("/portfolio/add", methods=["POST"])
def add_token():
    """Add a token to the portfolio."""
    body = request.get_json(force=True, silent=True) or {}

    address = (body.get("address") or "").strip()
    token_id = (body.get("id") or "").strip()
    name = (body.get("name") or "").strip()
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    if not address:
        return jsonify({"error": "Token address is required"}), 400
    if not token_id:
        return jsonify({"error": "Token id is required"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    portfolio = load_portfolio()
    tokens = portfolio.setdefault("tokens", [])

    # Update existing entry if the address already exists
    for token in tokens:
        if token.get("address", "").lower() == address.lower():
            token["amount"] = amount
            token["id"] = token_id
            token["name"] = name
            save_portfolio(portfolio)
            return jsonify({"message": "Token updated", "token": token})

    new_token = {"address": address, "id": token_id, "name": name, "amount": amount}
    tokens.append(new_token)
    save_portfolio(portfolio)
    return jsonify({"message": "Token added", "token": new_token}), 201


@app.route("/portfolio/token/<path:address>", methods=["DELETE"])
def remove_token(address):
    """Remove a token from the portfolio by address."""
    portfolio = load_portfolio()
    tokens = portfolio.get("tokens", [])
    original_count = len(tokens)

    portfolio["tokens"] = [
        t for t in tokens if t.get("address", "").lower() != address.lower()
    ]

    if len(portfolio["tokens"]) == original_count:
        return jsonify({"error": "Token not found"}), 404

    save_portfolio(portfolio)
    return jsonify({"message": "Token removed"})


# ── Stripe pages ──────────────────────────────────────────────────────────


@app.route("/deposit")
def deposit_page():
    """Render the multi-currency deposit form."""
    return render_template("deposit.html")


@app.route("/withdraw")
def withdraw_page():
    """Render the multi-currency withdrawal form."""
    return render_template("withdraw.html")


# ── Stripe API endpoints ──────────────────────────────────────────────────


@app.route("/portfolio/deposit", methods=["POST"])
def deposit():
    """Create a Stripe PaymentIntent and log a pending deposit transaction.

    Request body (JSON):
        amount   – deposit amount in major currency units (e.g. 10.50)
        currency – one of eur, gbp, usd
    """
    body = request.get_json(force=True, silent=True) or {}
    currency = (body.get("currency") or "usd").strip().lower()

    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400
    if currency not in stripe_integration.SUPPORTED_CURRENCIES:
        return jsonify({"error": f"Unsupported currency: {currency}"}), 400

    amount_cents = int(round(amount * 100))

    try:
        intent = stripe_integration.create_payment_intent(
            amount_cents, currency, metadata={"source": "portfolio_manager"}
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe error creating PaymentIntent: %s", exc)
        return jsonify({"error": "Payment provider error. Please try again later."}), 502

    tx_store.log_transaction(
        stripe_id=intent["id"],
        transaction_type="deposit",
        amount=amount,
        currency=currency,
        status="pending",
    )

    return jsonify(
        {
            "client_secret": intent["client_secret"],
            "payment_intent_id": intent["id"],
            "amount": amount,
            "currency": currency,
        }
    ), 201


@app.route("/portfolio/withdraw", methods=["POST"])
def withdraw():
    """Create a Stripe Payout and log a pending payout transaction.

    Request body (JSON):
        amount   – withdrawal amount in major currency units (e.g. 10.50)
        currency – one of eur, gbp, usd
    """
    body = request.get_json(force=True, silent=True) or {}
    currency = (body.get("currency") or "usd").strip().lower()

    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400
    if currency not in stripe_integration.SUPPORTED_CURRENCIES:
        return jsonify({"error": f"Unsupported currency: {currency}"}), 400

    amount_cents = int(round(amount * 100))

    try:
        payout = stripe_integration.create_payout(
            amount_cents, currency, description="Portfolio withdrawal"
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe error creating Payout: %s", exc)
        return jsonify({"error": "Payment provider error. Please try again later."}), 502

    tx_store.log_transaction(
        stripe_id=payout["id"],
        transaction_type="payout",
        amount=amount,
        currency=currency,
        status="pending",
    )

    return jsonify(
        {
            "payout_id": payout["id"],
            "amount": amount,
            "currency": currency,
            "status": payout["status"],
        }
    ), 201


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        result = webhooks.handle_webhook(payload, sig_header)
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    return jsonify(result)


@app.route("/transactions", methods=["GET"])
def get_transactions():
    """Return all recorded transactions."""
    return jsonify({"transactions": tx_store.get_transactions()})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5001)
