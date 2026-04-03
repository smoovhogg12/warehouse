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

// ── Withdraw form ─────────────────────────────────────────────────────────────

async function submitWithdraw(event) {
  event.preventDefault();

  const amount = parseFloat(document.getElementById("withdraw-amount").value);
  const currency = document.getElementById("withdraw-currency").value;

  if (isNaN(amount) || amount <= 0) {
    showMessage("withdraw-message", "Please enter a valid amount greater than zero.", "error");
    return;
  }

  const btn = document.getElementById("withdraw-btn");
  btn.disabled = true;
  btn.textContent = "Processing…";

  try {
    const resp = await fetch(`${API_BASE}/portfolio/withdraw`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, currency }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      showMessage("withdraw-message", data.error || "Withdrawal failed.", "error");
      return;
    }

    // Show result
    document.getElementById("withdraw-result").classList.remove("hidden");
    document.getElementById("withdraw-section").classList.add("hidden");

    const tbody = document.getElementById("withdraw-result-body");
    tbody.innerHTML = `
      <tr><th>Payout ID</th><td>${escapeHtml(data.payout_id)}</td></tr>
      <tr><th>Amount</th><td>${formatCurrency(data.amount, data.currency)}</td></tr>
      <tr><th>Currency</th><td>${escapeHtml(data.currency.toUpperCase())}</td></tr>
      <tr><th>Status</th><td>${escapeHtml(data.status || "pending")}</td></tr>
    `;
  } catch (err) {
    showMessage("withdraw-message", `Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🏦 Request Withdrawal";
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("withdraw-form").addEventListener("submit", submitWithdraw);
});
