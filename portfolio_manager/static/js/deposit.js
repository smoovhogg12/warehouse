const API_BASE = "";

// ── Helpers ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str || ""));
  return div.innerHTML;
}

function showMessage(elId, text, type = "success") {
  const el = document.getElementById(elId);
  if (!el) return;
  el.textContent = text;
  el.className = `message ${type}`;
  setTimeout(() => {
    el.textContent = "";
    el.className = "message";
  }, 5000);
}

function formatCurrency(amount, currency) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

// ── Deposit form ─────────────────────────────────────────────────────────────

async function submitDeposit(event) {
  event.preventDefault();

  const amount = parseFloat(document.getElementById("deposit-amount").value);
  const currency = document.getElementById("deposit-currency").value;

  if (isNaN(amount) || amount <= 0) {
    showMessage("deposit-message", "Please enter a valid amount greater than zero.", "error");
    return;
  }

  const btn = document.getElementById("deposit-btn");
  btn.disabled = true;
  btn.textContent = "Processing…";

  try {
    const resp = await fetch(`${API_BASE}/portfolio/deposit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, currency }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      showMessage("deposit-message", data.error || "Deposit failed.", "error");
      return;
    }

    // Show result
    document.getElementById("deposit-result").classList.remove("hidden");
    document.getElementById("deposit-section").classList.add("hidden");

    const tbody = document.getElementById("deposit-result-body");
    tbody.innerHTML = `
      <tr><th>Payment Intent ID</th><td>${escapeHtml(data.payment_intent_id)}</td></tr>
      <tr><th>Amount</th><td>${formatCurrency(data.amount, data.currency)}</td></tr>
      <tr><th>Currency</th><td>${escapeHtml(data.currency.toUpperCase())}</td></tr>
      <tr><th>Status</th><td>Pending – awaiting payment confirmation</td></tr>
    `;
  } catch (err) {
    showMessage("deposit-message", `Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "💳 Create Deposit";
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("deposit-form").addEventListener("submit", submitDeposit);
});
