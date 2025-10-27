document.addEventListener("DOMContentLoaded", () => {
  loadCash();
  document.getElementById("refresh-btn").addEventListener("click", loadCash);
  document.querySelectorAll(".data-btn").forEach(btn =>
    btn.addEventListener("click", () => showData(btn.dataset.type))
  );
});

// ===== CASH FETCH + RENDER =====
async function loadCash() {
  const cashDisplay = document.getElementById("cash-amount");
  cashDisplay.textContent = "Loading...";

  try {
    const res = await fetch("/home/api/cash/");
    const data = await res.json();
    renderCash(data.cash_balance);
  } catch (err) {
    cashDisplay.textContent = "Error loading cash";
  }
}

function renderCash(amount) {
  const cashDisplay = document.getElementById("cash-amount");
  const formatted = amount.toLocaleString(undefined, { minimumFractionDigits: 2 });
  cashDisplay.textContent = `AED ${formatted}`;
}

// ===== UNIVERSAL FETCHER =====
async function showData(type) {
  const urlMap = {
    party: "/home/api/party-balances/",
    expense: "/home/api/expense-party-balances/",
    parties: "/home/api/parties/",
    items: "/home/api/items/"
  };

  try {
    const res = await fetch(urlMap[type]);
    const data = await res.json();
    renderPopup(type, data);
  } catch (err) {
    Swal.fire("Error", "Unable to fetch data", "error");
  }
}

// ===== POPUP RENDERING =====
function renderPopup(type, data) {
  let title = "";
  let html = "";

  switch (type) {
    case "party":
      title = "👥 Party Balances";
      html = renderTable(data, ["name", "balance"]);
      break;
    case "expense":
      title = "💸 Expense Parties";
      html = renderTable(data, ["name", "balance"]);
      break;
    case "parties":
      title = "🏢 All Parties";
      html = renderTable(data, ["party_name", "party_type"]);
      break;
    case "items":
      title = "📦 Items List";
      html = renderTable(data, ["item_name", "brand"]);
      break;
  }

  Swal.fire({
    title,
    html: `
      <div class="popup-wrapper">
        <input type="text" id="searchBox" class="search-input" placeholder="🔍 Search..." />
        ${html}
      </div>
    `,
    width: 700,
    confirmButtonColor: "#7c807cff",
    didOpen: () => initSearchFilter(),
  });
}

// --- Filter logic ---
function initSearchFilter() {
  const input = document.getElementById("searchBox");
  const rows = document.querySelectorAll(".scroll-table tbody tr");
  input.addEventListener("input", () => {
    const term = input.value.toLowerCase();
    rows.forEach(row => {
      const visible = [...row.children].some(td =>
        td.textContent.toLowerCase().includes(term)
      );
      row.style.display = visible ? "" : "none";
    });
  });
}


// ===== GENERIC TABLE RENDERER =====
function renderTable(rows, columns) {
  if (!rows || rows.length === 0) return "<p>No data found.</p>";

  let html = "<div class='scroll-table'><table><thead><tr>";
  columns.forEach(col => (html += `<th>${toTitleCase(col)}</th>`));
  html += "</tr></thead><tbody>";

  rows.forEach(row => {
    html += "<tr>";
    columns.forEach(col => (html += `<td>${row[col] ?? ""}</td>`));
    html += "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}

function toTitleCase(str) {
  return str.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}
