// ==========================
// 🧭 Report Selector
// ==========================
function selectReport(type) {
  $(".report-btn").removeClass("active");
  if (type === "sale") {
    $("#btn-sale").addClass("active");
    $("#download_pdf").show(); // ✅ Show PDF button
    renderSaleProfitForm();
  } else {
    $("#btn-company").addClass("active");
    $("#download_pdf").hide(); // ✅ Hide PDF button
    $("#report-form-container").html("");
    fetchCompanyValuation();
  }

  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);
}


// ==========================
// 💰 Sale-wise Profit Form
// ==========================
function renderSaleProfitForm() {
  const today = new Date().toISOString().split("T")[0];
  const fromDefault = "2000-01-01";
  const formHTML = `
    <div class="form-row">
      <input type="date" id="from_date" value="${fromDefault}">
      <input type="date" id="to_date" value="${today}">
      <button class="generate-btn" onclick="fetchSaleProfit()">Generate</button>
    </div>
  `;
  $("#report-form-container").html(formHTML);
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Enter filters to generate report</td></tr>`);
}

// ==========================
// 📘 Fetch Sale-wise Profit
// ==========================
function fetchSaleProfit() {
  const fromDate = $("#from_date").val();
  const toDate = $("#to_date").val();

  if (!fromDate || !toDate) {
    Swal.fire("Missing Fields", "Please fill all input fields.", "warning");
    return;
  }

  Swal.fire({
    title: "Fetching...",
    text: "Please wait while sale-wise profit report loads.",
    didOpen: () => Swal.showLoading(),
    allowOutsideClick: false,
  });

  fetch("/accountsReports/sale-wise-report/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
  })
    .then((res) => res.json())
    .then((data) => {
      Swal.close();
      if (data.error) Swal.fire("Error", data.error, "error");
      else renderTable(data);
    })
    .catch(() => Swal.fire("Error", "Unable to fetch report data.", "error"));
}

// ==========================
// 🏢 Fetch Company Valuation
// ==========================
function fetchCompanyValuation() {
  Swal.fire({
    title: "Loading Company Valuation...",
    didOpen: () => Swal.showLoading(),
    allowOutsideClick: false,
  });

  fetch("/accountsReports/company-valuation/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
  })
    .then((res) => res.json())
    .then((data) => {
      Swal.close();
      if (data.error) Swal.fire("Error", data.error, "error");
      else renderCompanyValuation(data);
    })
    .catch(() => Swal.fire("Error", "Unable to fetch company valuation.", "error"));
}

// ==========================
// 🧱 Render Table
// ==========================
function renderTable(data) {
  const header = $("#reportHeader");
  const body = $("#reportBody");

  if (!data || data.length === 0) {
    header.html("");
    body.html(`<tr><td class="no-data">No records found</td></tr>`);
    return;
  }

  const cols = Object.keys(data[0]);
  header.html(`<tr>${cols.map((c) => `<th>${c.replace(/_/g, " ")}</th>`).join("")}</tr>`);
  body.html(
    data
      .map(
        (row) =>
          `<tr>${cols.map((c) => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`
      )
      .join("")
  );
}

function renderCompanyValuation(data) {
  const { financial_position, profit_and_loss } = data;

  if (!financial_position || !profit_and_loss) {
    $("#reportHeader").html("");
    $("#reportBody").html(`<tr><td class="no-data">Incomplete data</td></tr>`);
    return;
  }

  // Build content
  const html = `
    <div class="valuation-section">
      <h3>Financial Position</h3>
      <table class="valuation-table">
        <tr><th>Total Assets</th><td>${formatCurrency(financial_position.total_assets)}</td></tr>
        <tr><th>Total Liabilities</th><td>${formatCurrency(financial_position.total_liabilities)}</td></tr>
        <tr><th>Total Equity</th><td>${formatCurrency(financial_position.total_equity)}</td></tr>
        <tr class="highlight"><th>Net Worth</th><td>${formatCurrency(financial_position.net_worth)}</td></tr>
      </table>
    </div>

    <div class="valuation-section">
      <h3>Profit & Loss Summary</h3>
      <table class="valuation-table">
        <tr><th>Total Revenue</th><td>${formatCurrency(profit_and_loss.total_revenue)}</td></tr>
        <tr><th>Total Expenses</th><td>${formatCurrency(profit_and_loss.total_expenses)}</td></tr>
        <tr class="highlight"><th>Net Profit / Loss</th><td>${formatCurrency(profit_and_loss.net_profit_loss)}</td></tr>
      </table>
    </div>
  `;

  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td colspan="100%">${html}</td></tr>`);
}

// 💲 Utility: Format currency
function formatCurrency(value) {
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency: "PKR",
    minimumFractionDigits: 2,
  }).format(value || 0);
}


// ==========================
// 📄 Download PDF
// ==========================
$(document).on("click", "#download_pdf", function () {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "pt", "a4");

  const activeReport = $(".report-btn.active").attr("id") === "btn-sale"
    ? "Sale-wise Profit"
    : "Company Valuation";
  const fromDate = $("#from_date").val() || "N/A";
  const toDate = $("#to_date").val() || "N/A";

  doc.setFontSize(14);
  doc.text(`${activeReport} Report`, 40, 40);
  doc.setFontSize(10);
  if (activeReport === "Sale-wise Profit") doc.text(`From: ${fromDate}  To: ${toDate}`, 40, 60);

  doc.autoTable({
    html: "#reportTable",
    startY: activeReport === "Sale-wise Profit" ? 80 : 60,
    theme: "grid",
    headStyles: { fillColor: [25, 135, 84] },
    styles: { fontSize: 9 },
  });

  const filename = `${activeReport.replace(/ /g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
  doc.save(filename);
});

// ==========================
// 🔐 CSRF Token Utility
// ==========================
function getCSRFToken() {
  const name = "csrftoken=";
  const decodedCookie = decodeURIComponent(document.cookie);
  for (let c of decodedCookie.split(";")) {
    c = c.trim();
    if (c.indexOf(name) === 0) return c.substring(name.length, c.length);
  }
  return "";
}

// ==========================
// 🚀 Init Default View
// ==========================
$(document).ready(() => {
  selectReport("company");
});
