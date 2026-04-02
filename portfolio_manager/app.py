import json
import os

import requests
from flask import Flask, jsonify, render_template, request

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


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5001)
