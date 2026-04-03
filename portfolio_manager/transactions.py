"""Transaction logging helpers for portfolio manager Stripe integration."""

import json
import os
from datetime import datetime, timezone

TRANSACTIONS_FILE = os.path.join(os.path.dirname(__file__), "transactions.json")


def _load_transactions() -> list:
    if not os.path.exists(TRANSACTIONS_FILE):
        return []
    with open(TRANSACTIONS_FILE) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_transactions(transactions: list) -> None:
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions, f, indent=2)


def log_transaction(
    stripe_id: str,
    transaction_type: str,
    amount: float,
    currency: str,
    status: str = "pending",
    metadata: dict | None = None,
) -> dict:
    """Append a new transaction record and persist it.

    Args:
        stripe_id: The Stripe object ID (e.g. ``pi_xxx`` or ``po_xxx``).
        transaction_type: ``'deposit'`` or ``'payout'``.
        amount: Amount in major currency units (e.g. 10.50 for $10.50).
        currency: ISO 4217 lowercase currency code.
        status: Initial status, defaults to ``'pending'``.
        metadata: Optional extra metadata dict.

    Returns:
        The newly created transaction record dict.
    """
    transactions = _load_transactions()
    record = {
        "id": stripe_id,
        "type": transaction_type,
        "amount": amount,
        "currency": currency.lower(),
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    transactions.append(record)
    _save_transactions(transactions)
    return record


def update_transaction_status(stripe_id: str, status: str) -> bool:
    """Update the status of an existing transaction.

    Args:
        stripe_id: The Stripe object ID used to find the record.
        status: New status string (e.g. ``'completed'``, ``'failed'``).

    Returns:
        ``True`` if a matching record was found and updated, ``False`` otherwise.
    """
    transactions = _load_transactions()
    updated = False
    for tx in transactions:
        if tx.get("id") == stripe_id:
            tx["status"] = status
            updated = True
    if updated:
        _save_transactions(transactions)
    return updated


def get_transactions() -> list:
    """Return all recorded transactions."""
    return _load_transactions()
