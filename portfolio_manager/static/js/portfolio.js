const API_BASE = "";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatUSD(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(value);
}

function formatCurrency(amount, currency) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function showMessage(text, type = "success") {
  const el = document.getElementById("form-message");
  el.textContent = text;
  el.className = `message ${type}`;
  setTimeout(() => {
    el.textContent = "";
    el.className = "message";
  }, 4000);
}

// ── Currency balances ──────────────────────────────────────────────────────

async function loadBalances() {
  const container = document.getElementById("balances-container");
  if (!container) return;

  try {
    const resp = await fetch(`${API_BASE}/transactions`);
    if (!resp.ok) throw new Error("Failed to fetch transactions");
    const data = await resp.json();
    const transactions = data.transactions || [];

    // Aggregate completed deposits and payouts per currency
    const balances = { usd: 0, eur: 0, gbp: 0 };
    for (const tx of transactions) {
      if (tx.status !== "completed") continue;
      const cur = (tx.currency || "usd").toLowerCase();
      if (!(cur in balances)) balances[cur] = 0;
      if (tx.type === "deposit") {
        balances[cur] += tx.amount;
      } else if (tx.type === "payout") {
        balances[cur] -= tx.amount;
      }
    }

    const currencyLabels = { usd: "🇺🇸 USD", eur: "🇪🇺 EUR", gbp: "🇬🇧 GBP" };
    container.innerHTML = Object.entries(balances)
      .map(
        ([cur, bal]) => `
        <div class="balance-chip">
          <span class="balance-label">${currencyLabels[cur] || cur.toUpperCase()}</span>
          <span class="balance-amount">${formatCurrency(bal, cur)}</span>
        </div>`
      )
      .join("");
  } catch (_err) {
    console.error("Failed to load currency balances:", _err);
    container.innerHTML = '<p class="empty-message">Unable to load balances.</p>';
  }
}

// ── Fetch & render portfolio ───────────────────────────────────────────────

async function loadPortfolio() {
  const loading = document.getElementById("loading");
  const noTokens = document.getElementById("no-tokens");
  const tbody = document.getElementById("portfolio-body");
  const totalEl = document.getElementById("total-value");

  loading.classList.remove("hidden");
  noTokens.classList.add("hidden");
  tbody.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/portfolio`);
    if (!resp.ok) throw new Error("Failed to fetch portfolio");
    const data = await resp.json();

    loading.classList.add("hidden");
    const tokens = data.tokens || [];

    if (tokens.length === 0) {
      noTokens.classList.remove("hidden");
      totalEl.textContent = formatUSD(0);
      return;
    }

    tokens.forEach((token) => {
      const tr = document.createElement("tr");
      tr.dataset.address = token.address;
      tr.innerHTML = `
        <td><span class="token-name">${escapeHtml(token.name || token.id)}</span></td>
        <td><span class="address-cell" title="${escapeHtml(token.address)}">${escapeHtml(token.address)}</span></td>
        <td>${Number(token.amount).toLocaleString()}</td>
        <td>${formatUSD(token.price_usd)}</td>
        <td>${formatUSD(token.value_usd)}</td>
        <td>
          <button class="btn btn-danger" data-address="${escapeHtml(token.address)}">
            🗑 Remove
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Attach delete handlers
    tbody.querySelectorAll("[data-address]").forEach((btn) => {
      btn.addEventListener("click", () => removeToken(btn.dataset.address));
    });

    totalEl.textContent = formatUSD(data.total_value_usd);
  } catch (err) {
    loading.classList.add("hidden");
    showMessage(`Error loading portfolio: ${err.message}`, "error");
  }
}

// ── Add token ──────────────────────────────────────────────────────────────

async function addToken(event) {
  event.preventDefault();

  const address = document.getElementById("token-address").value.trim();
  const id = document.getElementById("token-id").value.trim();
  const name = document.getElementById("token-name").value.trim();
  const amount = parseFloat(document.getElementById("token-amount").value);

  if (!address || !id || isNaN(amount) || amount <= 0) {
    showMessage("Please fill in all required fields with valid values.", "error");
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/portfolio/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, id, name, amount }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      showMessage(data.error || "Failed to add token", "error");
      return;
    }

    showMessage(data.message || "Token added successfully", "success");
    document.getElementById("add-form").reset();
    loadPortfolio();
  } catch (err) {
    showMessage(`Error: ${err.message}`, "error");
  }
}

// ── Remove token ───────────────────────────────────────────────────────────

async function removeToken(address) {
  if (!confirm(`Remove token ${address} from portfolio?`)) return;

  try {
    const resp = await fetch(
      `${API_BASE}/portfolio/token/${encodeURIComponent(address)}`,
      { method: "DELETE" }
    );
    const data = await resp.json();

    if (!resp.ok) {
      showMessage(data.error || "Failed to remove token", "error");
      return;
    }

    showMessage(data.message || "Token removed", "success");
    loadPortfolio();
  } catch (err) {
    showMessage(`Error: ${err.message}`, "error");
  }
}

// ── XSS helper ────────────────────────────────────────────────────────────

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str || ""));
  return div.innerHTML;
}

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  loadPortfolio();
  loadBalances();
  document.getElementById("add-form").addEventListener("submit", addToken);
  document
    .getElementById("refresh-btn")
    .addEventListener("click", loadPortfolio);
  document
    .getElementById("balances-refresh-btn")
    .addEventListener("click", loadBalances);
});
