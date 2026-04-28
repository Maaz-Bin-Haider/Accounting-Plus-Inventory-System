/* ============================================================
   PROFIT REPORTS  —  JavaScript  (v3-final)
   • Compact filter form for sale-wise profit
   • Post-render table search/filter with row count
   • Professional branded PDF (amber/gold header)
   • CSV exports visible rows only
   ============================================================ */

let _rMeta = { title: "Profit Report", subtitle: "", filters: {} };

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function getCSRFToken() {
  for (let c of decodeURIComponent(document.cookie).split(";")) {
    c = c.trim();
    if (c.startsWith("csrftoken=")) return c.slice("csrftoken=".length);
  }
  return "";
}

function showLoader(msg = "Loading…") {
  Swal.fire({ title: msg, didOpen: () => Swal.showLoading(), allowOutsideClick: false });
}

function fmt(date) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-PK", {
    style: "currency", currency: "PKR", minimumFractionDigits: 2,
  }).format(value || 0);
}

// ═══════════════════════════════════════════
// REPORT SELECTOR
// ═══════════════════════════════════════════
function selectReport(type) {
  $(".report-btn").removeClass("active");
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Loading…</td></tr>`);
  $("#reportToolbar").remove();
  $("#report-form-container").html("");

  if (type === "sale") {
    $("#btn-sale").addClass("active");
    renderSaleProfitForm();
  } else {
    $("#btn-company").addClass("active");
    fetchCompanyValuation();
  }
}

// ═══════════════════════════════════════════
// FORM RENDERERS
// ═══════════════════════════════════════════

function renderSaleProfitForm() {
  const today = new Date().toISOString().split("T")[0];

  $("#report-form-container").html(`
    <div class="filter-form">
      <div class="filter-field">
        <label><i class="fa-regular fa-calendar"></i>&nbsp;From Date</label>
        <input type="date" id="from_date" value="2000-01-01">
      </div>
      <div class="filter-field">
        <label><i class="fa-regular fa-calendar"></i>&nbsp;To Date</label>
        <input type="date" id="to_date" value="${today}" max="${today}">
      </div>
      <button class="generate-btn" onclick="fetchSaleProfit()">
        <i class="fa-solid fa-bolt"></i> Generate
      </button>
    </div>
  `);
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Set a date range and click Generate</td></tr>`);
}

// ═══════════════════════════════════════════
// DATA FETCHERS
// ═══════════════════════════════════════════

function fetchSaleProfit() {
  const from = $("#from_date").val();
  const to   = $("#to_date").val();
  if (!from || !to) { Swal.fire("Missing Fields", "Please fill in both dates.", "warning"); return; }

  _rMeta = { title: "Sale-wise Profit", subtitle: "Profit & loss per sale transaction",
             filters: { From: fmt(from), To: fmt(to) } };
  showLoader("Fetching sale-wise profit…");

  fetch("/accountsReports/sale-wise-report/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify({ from_date: from, to_date: to })
  })
  .then(r => r.json())
  .then(data => { Swal.close(); data.error ? Swal.fire("Error", data.error, "error") : renderTable(data); })
  .catch(() => Swal.fire("Error", "Unable to fetch report data.", "error"));
}

function fetchCompanyValuation() {
  _rMeta = { title: "Company Valuation", subtitle: "Financial position and profit & loss summary", filters: {} };
  showLoader("Loading Company Valuation…");

  fetch("/accountsReports/company-valuation/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() }
  })
  .then(r => r.json())
  .then(data => { Swal.close(); data.error ? Swal.fire("Error", data.error, "error") : renderCompanyValuation(data); })
  .catch(() => Swal.fire("Error", "Unable to fetch company valuation.", "error"));
}

// ═══════════════════════════════════════════
// TABLE RENDERER
// ═══════════════════════════════════════════
function renderTable(data) {
  const $header = $("#reportHeader");
  const $body   = $("#reportBody");

  if (!data || !data.length) {
    $header.html("");
    $body.html(`<tr><td class="no-data">No records found</td></tr>`);
    injectToolbar(0);
    return;
  }

  const cols = Object.keys(data[0]);
  $header.html(`<tr>${cols.map(c => `<th>${c.replace(/_/g, " ")}</th>`).join("")}</tr>`);
  $body.html(data.map(row =>
    `<tr>${cols.map(c => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`
  ).join(""));

  injectToolbar(data.length);
}

// ── Company Valuation — special rich layout ──────────────────
function renderCompanyValuation(data) {
  const { financial_position: fp, profit_and_loss: pl } = data;

  if (!fp || !pl) {
    $("#reportHeader").html("");
    $("#reportBody").html(`<tr><td class="no-data">Incomplete valuation data</td></tr>`);
    return;
  }

  const netProfit   = pl.net_profit_loss || 0;
  const isProfit    = netProfit >= 0;
  const profitColor = isProfit ? "var(--brand-success)" : "var(--brand-danger)";
  const profitLabel = isProfit ? "Net Profit" : "Net Loss";

  const html = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;padding:0.25rem;">

      <!-- Financial Position -->
      <div class="valuation-section">
        <h3><i class="fa-solid fa-scale-balanced"></i> Financial Position</h3>
        <table class="valuation-table">
          <tr><th>Total Assets</th><td>${formatCurrency(fp.total_assets)}</td></tr>
          <tr><th>Total Liabilities</th><td style="color:var(--brand-danger)">${formatCurrency(fp.total_liabilities)}</td></tr>
          <tr><th>Total Equity</th><td>${formatCurrency(fp.total_equity)}</td></tr>
          <tr class="highlight"><th>Net Worth</th><td>${formatCurrency(fp.net_worth)}</td></tr>
        </table>
      </div>

      <!-- Profit & Loss -->
      <div class="valuation-section">
        <h3><i class="fa-solid fa-chart-line"></i> Profit &amp; Loss</h3>
        <table class="valuation-table">
          <tr><th>Total Revenue</th><td style="color:var(--brand-success)">${formatCurrency(pl.total_revenue)}</td></tr>
          <tr><th>Total Expenses</th><td style="color:var(--brand-danger)">${formatCurrency(pl.total_expenses)}</td></tr>
          <tr class="highlight"><th>${profitLabel}</th>
              <td style="color:${profitColor};font-size:1.05rem;">${formatCurrency(netProfit)}</td></tr>
        </table>
      </div>
    </div>
  `;

  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td colspan="100%" style="padding:0;">${html}</td></tr>`);
  // No toolbar needed for valuation (it's cards, not a filterable table)
}

// ═══════════════════════════════════════════
// TOOLBAR
// ═══════════════════════════════════════════
function injectToolbar(total) {
  $("#reportToolbar").remove();

  $(`<div id="reportToolbar" class="report-toolbar">
      <div class="table-filter-bar">
        <div class="table-search-wrap">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input type="text" id="tableSearch" placeholder="Filter results…" autocomplete="off">
        </div>
        <span class="table-row-count" id="rowCount">${total} row${total !== 1 ? "s" : ""}</span>
      </div>
      <div class="table-actions">
        <button id="download_pdf" class="btn-download">
          <i class="fa-solid fa-file-pdf"></i> PDF
        </button>
        <button id="download_csv" class="btn-download btn-csv">
          <i class="fa-solid fa-file-csv"></i> CSV
        </button>
      </div>
    </div>`).insertBefore(".table-container");

  $("#tableSearch").on("input", function () {
    const q = this.value.toLowerCase().trim();
    let vis = 0;
    $("#reportBody tr").each(function () {
      const show = !q || $(this).text().toLowerCase().includes(q);
      $(this).toggleClass("filtered-out", !show);
      if (show) vis++;
    });
    $("#rowCount").text(`${vis} row${vis !== 1 ? "s" : ""}`);
  });
}

// ═══════════════════════════════════════════
// PDF  —  amber branded header + footer
// ═══════════════════════════════════════════
$(document).on("click", "#download_pdf", function () {
  const { jsPDF } = window.jspdf;

  const colHeaders = [...document.querySelectorAll("#reportTable thead th")].map(th => th.textContent.trim());
  const rowData    = [];
  document.querySelectorAll("#reportBody tr:not(.filtered-out)").forEach(tr => {
    const cells = [...tr.querySelectorAll("td")].map(td => td.textContent.trim());
    if (cells.length && !cells[0].includes("No records") && !cells[0].includes("valuation-section"))
      rowData.push(cells);
  });

  if (!rowData.length || !colHeaders.length) {
    Swal.fire("No Data", "Nothing visible to export as PDF.\nFor Company Valuation, use the browser print function.", "info");
    return;
  }

  const doc   = new jsPDF("l", "pt", "a4");
  const pW    = doc.internal.pageSize.width;
  const pH    = doc.internal.pageSize.height;
  const today = new Date().toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
  const m     = _rMeta;
  const fStr  = Object.entries(m.filters || {}).map(([k, v]) => `${k}: ${v}`).join("   ·   ");

  function drawHeader(pg, total) {
    doc.setFillColor(180, 83, 9);              // amber-800 (profit/gold)
    doc.rect(0, 0, pW, 38, "F");
    doc.setFont("helvetica", "bold"); doc.setFontSize(13); doc.setTextColor(255, 255, 255);
    doc.text("Financee", 36, 25);
    doc.setFont("helvetica", "normal"); doc.setFontSize(10);
    doc.text(m.title, pW - 36, 25, { align: "right" });

    doc.setFillColor(255, 251, 235);           // amber-50
    doc.rect(0, 38, pW, 26, "F");
    doc.setFont("helvetica", "italic"); doc.setFontSize(8); doc.setTextColor(71, 85, 105);
    let sub = m.subtitle || "";
    if (fStr) sub += (sub ? "   ·   " : "") + fStr;
    doc.text(sub, 36, 55);
    doc.setFont("helvetica", "normal");
    doc.text(`Generated: ${today}   Page ${pg} of ${total}`, pW - 36, 55, { align: "right" });
    doc.setDrawColor(203, 213, 225); doc.setLineWidth(0.5); doc.line(0, 64, pW, 64);
  }

  function drawFooter(pg, total) {
    const y = pH - 18;
    doc.setDrawColor(226, 232, 240); doc.setLineWidth(0.4); doc.line(36, y - 7, pW - 36, y - 7);
    doc.setFont("helvetica", "normal"); doc.setFontSize(7.5); doc.setTextColor(148, 163, 184);
    doc.text("Financee  —  Confidential", 36, y + 2);
    doc.text(`Page ${pg} of ${total}`, pW - 36, y + 2, { align: "right" });
  }

  doc.autoTable({
    head: [colHeaders], body: rowData,
    startY: 72,
    margin: { left: 28, right: 28, top: 72, bottom: 32 },
    theme: "grid",
    headStyles:         { fillColor: [146, 64, 14], textColor: [255,255,255], fontStyle: "bold", fontSize: 7.5, cellPadding: 5 },
    bodyStyles:         { fontSize: 7.5, textColor: [30, 41, 59], cellPadding: 4, lineColor: [226, 232, 240] },
    alternateRowStyles: { fillColor: [255, 251, 235] },
    didDrawPage: d => drawHeader(d.pageNumber, "…"),
  });

  const totalPg = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPg; i++) { doc.setPage(i); drawHeader(i, totalPg); drawFooter(i, totalPg); }

  doc.save(`${m.title.replace(/\s+/g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`);
});

// ═══════════════════════════════════════════
// CSV
// ═══════════════════════════════════════════
$(document).on("click", "#download_csv", function () {
  const tbl = document.getElementById("reportTable");
  if (!tbl) { Swal.fire("No Data", "Nothing to export.", "warning"); return; }

  const m    = _rMeta;
  const rows = [];
  rows.push([`${m.title} Report`]);
  Object.entries(m.filters || {}).forEach(([k, v]) => rows.push([`${k}: ${v}`]));
  rows.push([`Generated: ${new Date().toLocaleString()}`]);
  rows.push([]);
  rows.push([...tbl.querySelectorAll("thead th")].map(th => th.textContent.trim()));

  tbl.querySelectorAll("tbody tr:not(.filtered-out)").forEach(tr => {
    const row = [...tr.querySelectorAll("td")].map(td => {
      let v = td.textContent.trim();
      if (/[,"\n]/.test(v)) v = `"${v.replace(/"/g, '""')}"`;
      return v;
    });
    if (row.length && !row[0].includes("No records")) rows.push(row);
  });

  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([rows.map(r => r.join(",")).join("\n")], { type: "text/csv;charset=utf-8;" })),
    download: `${m.title.replace(/\s+/g,"_")}_${new Date().toISOString().split("T")[0]}.csv`,
    style: "display:none",
  });
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
});

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
$(document).ready(() => selectReport("company"));
