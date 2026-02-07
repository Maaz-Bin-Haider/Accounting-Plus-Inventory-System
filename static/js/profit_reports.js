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


// // ==========================
// // 📄 Download PDF
// // ==========================
// $(document).on("click", "#download_pdf", function () {
//   const { jsPDF } = window.jspdf;
//   const doc = new jsPDF("p", "pt", "a4");

//   const activeReport = $(".report-btn.active").attr("id") === "btn-sale"
//     ? "Sale-wise Profit"
//     : "Company Valuation";
//   const fromDate = $("#from_date").val() || "N/A";
//   const toDate = $("#to_date").val() || "N/A";

//   doc.setFontSize(14);
//   doc.text(`${activeReport} Report`, 40, 40);
//   doc.setFontSize(10);
//   if (activeReport === "Sale-wise Profit") doc.text(`From: ${fromDate}  To: ${toDate}`, 40, 60);

//   doc.autoTable({
//     html: "#reportTable",
//     startY: activeReport === "Sale-wise Profit" ? 80 : 60,
//     theme: "grid",
//     headStyles: { fillColor: [25, 135, 84] },
//     styles: { fontSize: 9 },
//   });

//   const filename = `${activeReport.replace(/ /g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
//   doc.save(filename);
// });

// // ==========================
// // 📄 Download PDF - UPDATED with Totals/Averages
// // ==========================
// $(document).on("click", "#download_pdf", function () {
//   const { jsPDF } = window.jspdf;
//   const doc = new jsPDF("p", "pt", "a4");

//   const activeReport = $(".report-btn.active").attr("id") === "btn-sale"
//     ? "Sale-wise Profit"
//     : "Company Valuation";
//   const fromDate = $("#from_date").val() || "N/A";
//   const toDate = $("#to_date").val() || "N/A";

//   doc.setFontSize(14);
//   doc.text(`${activeReport} Report`, 40, 40);
//   doc.setFontSize(10);
//   if (activeReport === "Sale-wise Profit") doc.text(`From: ${fromDate}  To: ${toDate}`, 40, 60);

//   // Calculate totals and averages for Sale-wise Profit report
//   let footerRows = [];
//   if (activeReport === "Sale-wise Profit") {
//     const table = document.getElementById("reportTable");
//     if (table && table.querySelector("tbody")) {
//       let totalSalePrice = 0;
//       let totalPurchasePrice = 0;
//       let totalProfitLoss = 0;
//       let validProfitPercentCount = 0;
//       let sumProfitPercent = 0;

//       // Find column indices
//       const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
//       const salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
//       const purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
//       const profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
//       const profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));

//       // Calculate sums
//       table.querySelectorAll("tbody tr").forEach(row => {
//         const cells = row.querySelectorAll("td");
//         if (cells.length > 0) {
//           // Sale Price
//           if (salePriceIdx >= 0 && cells[salePriceIdx]) {
//             const value = parseFloat(cells[salePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalSalePrice += value;
//           }
//           // Purchase Price
//           if (purchasePriceIdx >= 0 && cells[purchasePriceIdx]) {
//             const value = parseFloat(cells[purchasePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalPurchasePrice += value;
//           }
//           // Profit/Loss
//           if (profitLossIdx >= 0 && cells[profitLossIdx]) {
//             const value = parseFloat(cells[profitLossIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalProfitLoss += value;
//           }
//           // Profit/Loss %
//           if (profitPercentIdx >= 0 && cells[profitPercentIdx]) {
//             const value = parseFloat(cells[profitPercentIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) {
//               sumProfitPercent += value;
//               validProfitPercentCount++;
//             }
//           }
//         }
//       });

//       const avgProfitPercent = validProfitPercentCount > 0 
//         ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
//         : "0.00";

//       // Create footer row with totals
//       const footerRow = new Array(headers.length).fill("");
//       footerRow[0] = "TOTAL";
//       if (salePriceIdx >= 0) footerRow[salePriceIdx] = totalSalePrice.toFixed(2);
//       if (purchasePriceIdx >= 0) footerRow[purchasePriceIdx] = totalPurchasePrice.toFixed(2);
//       if (profitLossIdx >= 0) footerRow[profitLossIdx] = totalProfitLoss.toFixed(2);
//       if (profitPercentIdx >= 0) footerRow[profitPercentIdx] = avgProfitPercent + " (avg)";

//       footerRows = [footerRow];
//     }
//   }

//   doc.autoTable({
//     html: "#reportTable",
//     startY: activeReport === "Sale-wise Profit" ? 80 : 60,
//     theme: "grid",
//     headStyles: { fillColor: [25, 135, 84] },
//     styles: { fontSize: 9 },
//     // Add footer with totals for Sale-wise Profit
//     didDrawPage: function(data) {
//       if (activeReport === "Sale-wise Profit" && footerRows.length > 0) {
//         const finalY = data.cursor.y;
//         doc.autoTable({
//           startY: finalY,
//           head: [],
//           body: footerRows,
//           theme: "grid",
//           styles: { 
//             fontSize: 9, 
//             fontStyle: "bold",
//             fillColor: [240, 240, 240]
//           },
//           columnStyles: data.settings.columnStyles,
//           margin: { left: data.settings.margin.left }
//         });
//       }
//     }
//   });

//   const filename = `${activeReport.replace(/ /g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
//   doc.save(filename);
// });

// // ==========================
// // 📄 Download PDF - FIXED: Landscape + Totals at End Only
// // ==========================
// $(document).on("click", "#download_pdf", function () {
//   const { jsPDF } = window.jspdf;
  
//   const activeReport = $(".report-btn.active").attr("id") === "btn-sale"
//     ? "Sale-wise Profit"
//     : "Company Valuation";
//   const fromDate = $("#from_date").val() || "N/A";
//   const toDate = $("#to_date").val() || "N/A";

//   // Use landscape orientation for Sale-wise Profit to accommodate more columns
//   const orientation = activeReport === "Sale-wise Profit" ? "l" : "p";
//   const doc = new jsPDF(orientation, "pt", "a4");

//   doc.setFontSize(14);
//   doc.text(`${activeReport} Report`, 40, 40);
//   doc.setFontSize(10);
//   if (activeReport === "Sale-wise Profit") doc.text(`From: ${fromDate}  To: ${toDate}`, 40, 60);

//   // Calculate totals and averages for Sale-wise Profit report
//   let totalSalePrice = 0;
//   let totalPurchasePrice = 0;
//   let totalProfitLoss = 0;
//   let validProfitPercentCount = 0;
//   let sumProfitPercent = 0;
//   let hasData = false;

//   if (activeReport === "Sale-wise Profit") {
//     const table = document.getElementById("reportTable");
//     if (table && table.querySelector("tbody")) {
//       // Find column indices
//       const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
//       const salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
//       const purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
//       const profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
//       const profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));

//       // Calculate sums
//       table.querySelectorAll("tbody tr").forEach(row => {
//         const cells = row.querySelectorAll("td");
//         if (cells.length > 0) {
//           hasData = true;
//           // Sale Price
//           if (salePriceIdx >= 0 && cells[salePriceIdx]) {
//             const value = parseFloat(cells[salePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalSalePrice += value;
//           }
//           // Purchase Price
//           if (purchasePriceIdx >= 0 && cells[purchasePriceIdx]) {
//             const value = parseFloat(cells[purchasePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalPurchasePrice += value;
//           }
//           // Profit/Loss
//           if (profitLossIdx >= 0 && cells[profitLossIdx]) {
//             const value = parseFloat(cells[profitLossIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) totalProfitLoss += value;
//           }
//           // Profit/Loss %
//           if (profitPercentIdx >= 0 && cells[profitPercentIdx]) {
//             const value = parseFloat(cells[profitPercentIdx].textContent.replace(/[^0-9.-]/g, ""));
//             if (!isNaN(value)) {
//               sumProfitPercent += value;
//               validProfitPercentCount++;
//             }
//           }
//         }
//       });
//     }
//   }

//   // Generate main table
//   const autoTableResult = doc.autoTable({
//     html: "#reportTable",
//     startY: activeReport === "Sale-wise Profit" ? 80 : 60,
//     theme: "grid",
//     headStyles: { fillColor: [25, 135, 84] },
//     styles: { fontSize: 9 },
//     // Adjust column widths for better spacing (especially for item name and serial number)
//     columnStyles: activeReport === "Sale-wise Profit" ? {
//       0: { cellWidth: 60 },   // Sale Date
//       1: { cellWidth: 120 },  // Item Name - wider
//       2: { cellWidth: 120 },   // Serial Number - wider
//       3: { cellWidth: 80 },  // Serial Comment
//       4: { cellWidth: 60 },   // Sale Price
//       5: { cellWidth: 70 },   // Purchase Price
//       6: { cellWidth: 60 },   // Profit/Loss
//       7: { cellWidth: 60 },   // Profit/Loss %
//       8: { cellWidth: 90 }    // Vendor Name
//     } : {}
//   });

//   // Add totals ONLY at the very end (after all pages are complete)
//   if (activeReport === "Sale-wise Profit" && hasData) {
//     const table = document.getElementById("reportTable");
//     const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
//     const salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
//     const purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
//     const profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
//     const profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));

//     const avgProfitPercent = validProfitPercentCount > 0 
//       ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
//       : "0.00";

//     // Create footer row with totals
//     const footerRow = new Array(headers.length).fill("");
//     footerRow[0] = "TOTAL";
//     if (salePriceIdx >= 0) footerRow[salePriceIdx] = totalSalePrice.toFixed(2);
//     if (purchasePriceIdx >= 0) footerRow[purchasePriceIdx] = totalPurchasePrice.toFixed(2);
//     if (profitLossIdx >= 0) footerRow[profitLossIdx] = totalProfitLoss.toFixed(2);
//     if (profitPercentIdx >= 0) footerRow[profitPercentIdx] = (avgProfitPercent/100) + "% (avg)";

//     // Get the final Y position from the last table
//     const finalY = doc.lastAutoTable.finalY;

//     // Add totals table at the end
//     doc.autoTable({
//       startY: finalY,
//       head: [],
//       body: [footerRow],
//       theme: "grid",
//       styles: { 
//         fontSize: 9, 
//         fontStyle: "bold",
//         fillColor: [240, 240, 240]
//       },
//       headStyles: { fillColor: [25, 135, 84] },
//       columnStyles: activeReport === "Sale-wise Profit" ? {
//         0: { cellWidth: 60 },
//         1: { cellWidth: 120 },
//         2: { cellWidth: 120 },
//         3: { cellWidth: 80 },
//         4: { cellWidth: 60 },
//         5: { cellWidth: 70 },
//         6: { cellWidth: 60 },
//         7: { cellWidth: 60 },
//         8: { cellWidth: 90 }
//       } : {}
//     });
//   }

//   const filename = `${activeReport.replace(/ /g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
//   doc.save(filename);
// });

// ==========================
// 📄 Download PDF - With Conditional Row Highlighting
// ==========================
$(document).on("click", "#download_pdf", function () {
  const { jsPDF } = window.jspdf;
  
  const activeReport = $(".report-btn.active").attr("id") === "btn-sale"
    ? "Sale-wise Profit"
    : "Company Valuation";
  const fromDate = $("#from_date").val() || "N/A";
  const toDate = $("#to_date").val() || "N/A";

  // Use landscape orientation for Sale-wise Profit to accommodate more columns
  const orientation = activeReport === "Sale-wise Profit" ? "l" : "p";
  const doc = new jsPDF(orientation, "pt", "a4");

  doc.setFontSize(14);
  doc.text(`${activeReport} Report`, 40, 40);
  doc.setFontSize(10);
  if (activeReport === "Sale-wise Profit") doc.text(`From: ${fromDate}  To: ${toDate}`, 40, 60);

  // Calculate totals and averages for Sale-wise Profit report
  let totalSalePrice = 0;
  let totalPurchasePrice = 0;
  let totalProfitLoss = 0;
  let validProfitPercentCount = 0;
  let sumProfitPercent = 0;
  let hasData = false;

  // Store column indices for highlighting logic
  let purchasePriceIdx = -1;
  let profitLossIdx = -1;

  if (activeReport === "Sale-wise Profit") {
    const table = document.getElementById("reportTable");
    if (table && table.querySelector("tbody")) {
      // Find column indices
      const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
      const salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
      purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
      profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
      const profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));

      // Calculate sums
      table.querySelectorAll("tbody tr").forEach(row => {
        const cells = row.querySelectorAll("td");
        if (cells.length > 0) {
          hasData = true;
          // Sale Price
          if (salePriceIdx >= 0 && cells[salePriceIdx]) {
            const value = parseFloat(cells[salePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
            if (!isNaN(value)) totalSalePrice += value;
          }
          // Purchase Price
          if (purchasePriceIdx >= 0 && cells[purchasePriceIdx]) {
            const value = parseFloat(cells[purchasePriceIdx].textContent.replace(/[^0-9.-]/g, ""));
            if (!isNaN(value)) totalPurchasePrice += value;
          }
          // Profit/Loss
          if (profitLossIdx >= 0 && cells[profitLossIdx]) {
            const value = parseFloat(cells[profitLossIdx].textContent.replace(/[^0-9.-]/g, ""));
            if (!isNaN(value)) totalProfitLoss += value;
          }
          // Profit/Loss %
          if (profitPercentIdx >= 0 && cells[profitPercentIdx]) {
            const value = parseFloat(cells[profitPercentIdx].textContent.replace(/[^0-9.-]/g, ""));
            if (!isNaN(value)) {
              sumProfitPercent += value;
              validProfitPercentCount++;
            }
          }
        }
      });
    }
  }

  // Generate main table with conditional row highlighting
  const autoTableResult = doc.autoTable({
    html: "#reportTable",
    startY: activeReport === "Sale-wise Profit" ? 80 : 60,
    theme: "grid",
    headStyles: { fillColor: [25, 135, 84] },
    styles: { fontSize: 9 },
    // Adjust column widths for better spacing (especially for item name and serial number)
    columnStyles: activeReport === "Sale-wise Profit" ? {
      0: { cellWidth: 60 },   // Sale Date
      1: { cellWidth: 120 },  // Item Name - wider
      2: { cellWidth: 130 },   // Serial Number - wider
      3: { cellWidth: 80 },  // Serial Comment
      4: { cellWidth: 60 },   // Sale Price
      5: { cellWidth: 60 },   // Purchase Price
      6: { cellWidth: 60 },   // Profit/Loss
      7: { cellWidth: 60 },   // Profit/Loss %
      8: { cellWidth: 90 }    // Vendor Name
    } : {},
    // Add conditional row highlighting for Sale-wise Profit
    didParseCell: function(data) {
      if (activeReport === "Sale-wise Profit" && data.section === 'body') {
        // Get the row data
        const rowCells = data.row.cells;
        
        // Check profit/loss value (negative = loss = red)
        let profitLossValue = null;
        if (profitLossIdx >= 0 && rowCells[profitLossIdx]) {
          const cellText = rowCells[profitLossIdx].text.join('');
          profitLossValue = parseFloat(cellText.replace(/[^0-9.-]/g, ""));
        }
        
        // Check purchase price value (= 1 = yellow)
        let purchasePriceValue = null;
        if (purchasePriceIdx >= 0 && rowCells[purchasePriceIdx]) {
          const cellText = rowCells[purchasePriceIdx].text.join('');
          purchasePriceValue = parseFloat(cellText.replace(/[^0-9.-]/g, ""));
        }
        
        // Priority: Red for loss (negative profit/loss)
        if (!isNaN(profitLossValue) && profitLossValue < 0) {
          data.cell.styles.fillColor = [255, 200, 200]; // Light red
        }
        // Yellow for purchase price = 1 (only if not already red)
        else if (!isNaN(purchasePriceValue) && purchasePriceValue === 1) {
          data.cell.styles.fillColor = [255, 255, 200]; // Light yellow
        }
      }
    }
  });

  // Add totals ONLY at the very end (after all pages are complete)
  if (activeReport === "Sale-wise Profit" && hasData) {
    const table = document.getElementById("reportTable");
    const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
    const salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
    purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
    profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
    const profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));

    const avgProfitPercent = validProfitPercentCount > 0 
      ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
      : "0.00";

    // Create footer row with totals
    const footerRow = new Array(headers.length).fill("");
    footerRow[0] = "TOTAL";
    if (salePriceIdx >= 0) footerRow[salePriceIdx] = totalSalePrice.toFixed(2);
    if (purchasePriceIdx >= 0) footerRow[purchasePriceIdx] = totalPurchasePrice.toFixed(2);
    if (profitLossIdx >= 0) footerRow[profitLossIdx] = totalProfitLoss.toFixed(2);
    if (profitPercentIdx >= 0) footerRow[profitPercentIdx] = (avgProfitPercent/100) + "% (avg)";

    // Get the final Y position from the last table
    const finalY = doc.lastAutoTable.finalY;

    // Add totals table at the end
    doc.autoTable({
      startY: finalY,
      head: [],
      body: [footerRow],
      theme: "grid",
      styles: { 
        fontSize: 9, 
        fontStyle: "bold",
        fillColor: [240, 240, 240]
      },
      headStyles: { fillColor: [25, 135, 84] },
      columnStyles: activeReport === "Sale-wise Profit" ? {
        0: { cellWidth: 60 },
        1: { cellWidth: 120 },
        2: { cellWidth: 130 },
        3: { cellWidth: 80 },
        4: { cellWidth: 60 },
        5: { cellWidth: 60 },
        6: { cellWidth: 60 },
        7: { cellWidth: 60 },
        8: { cellWidth: 90 }
      } : {}
    });
  }

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



// // ==========================
// // 📊 Download Table as CSV
// // ==========================
// $(document).on("click", "#download_csv", function () {
//   const activeBtn = $(".report-btn.active");
//   let activeReport = "Report";
//   let party = "";
//   let fromDate = "";
//   let toDate = "";

//   // Determine which report is active
//   if (activeBtn.attr("id") === "btn-ledger") {
//     activeReport = "Detailed_Ledger";
//     party = $("#search_name").val() || "All";
//     fromDate = $("#from_date").val() || "N/A";
//     toDate = $("#to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-cash-ledger") {
//     activeReport = "Cash_Ledger";
//     fromDate = $("#cash_from_date").val() || "N/A";
//     toDate = $("#cash_to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-trial") {
//     activeReport = "Trial_Balance";
//   }

//   // Get table data
//   const table = document.getElementById("reportTable");
//   if (!table || table.rows.length === 0) {
//     Swal.fire("No Data", "No data available to download.", "warning");
//     return;
//   }

//   let csv = [];
  
//   // Add metadata header
//   if (activeReport === "Detailed_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`Party: ${party}`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else if (activeReport === "Cash_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([]); // Empty row
//   }

//   // Extract headers
//   const headers = [];
//   const headerRow = table.querySelector("thead tr");
//   if (headerRow) {
//     headerRow.querySelectorAll("th").forEach(th => {
//       headers.push(th.textContent.trim());
//     });
//     csv.push(headers);
//   }

//   // Extract data rows
//   const tbody = table.querySelector("tbody");
//   if (tbody) {
//     tbody.querySelectorAll("tr").forEach(tr => {
//       const row = [];
//       tr.querySelectorAll("td").forEach(td => {
//         let cellData = td.textContent.trim();
//         // Escape quotes and wrap in quotes if contains comma
//         if (cellData.includes(",") || cellData.includes('"') || cellData.includes("\n")) {
//           cellData = '"' + cellData.replace(/"/g, '""') + '"';
//         }
//         row.push(cellData);
//       });
//       // Only add row if it's not the "no data" message
//       if (row.length > 0 && !row[0].includes("No records found") && !row[0].includes("Select a report")) {
//         csv.push(row);
//       }
//     });
//   }

//   // Convert to CSV string
//   const csvContent = csv.map(row => row.join(",")).join("\n");

//   // Create download link
//   const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
//   const link = document.createElement("a");
//   const url = URL.createObjectURL(blob);
  
//   link.setAttribute("href", url);
//   const filename = `${activeReport}_${new Date().toISOString().split("T")[0]}.csv`;
//   link.setAttribute("download", filename);
//   link.style.visibility = "hidden";
  
//   document.body.appendChild(link);
//   link.click();
//   document.body.removeChild(link);
// });


// // ==========================
// // 📊 Download Table as CSV - UPDATED with Totals/Averages
// // ==========================
// $(document).on("click", "#download_csv", function () {
//   const activeBtn = $(".report-btn.active");
//   let activeReport = "Report";
//   let party = "";
//   let fromDate = "";
//   let toDate = "";

//   // Determine which report is active
//   if (activeBtn.attr("id") === "btn-ledger") {
//     activeReport = "Detailed_Ledger";
//     party = $("#search_name").val() || "All";
//     fromDate = $("#from_date").val() || "N/A";
//     toDate = $("#to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-cash-ledger") {
//     activeReport = "Cash_Ledger";
//     fromDate = $("#cash_from_date").val() || "N/A";
//     toDate = $("#cash_to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-trial") {
//     activeReport = "Trial_Balance";
//   } else if (activeBtn.attr("id") === "btn-sale") {
//     activeReport = "Sale_wise_Profit";
//     fromDate = $("#from_date").val() || "N/A";
//     toDate = $("#to_date").val() || "N/A";
//   }

//   // Get table data
//   const table = document.getElementById("reportTable");
//   if (!table || table.rows.length === 0) {
//     Swal.fire("No Data", "No data available to download.", "warning");
//     return;
//   }

//   let csv = [];
  
//   // Add metadata header
//   if (activeReport === "Detailed_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`Party: ${party}`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else if (activeReport === "Cash_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else if (activeReport === "Sale_wise_Profit") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([]); // Empty row
//   }

//   // Extract headers
//   const headers = [];
//   const headerRow = table.querySelector("thead tr");
//   if (headerRow) {
//     headerRow.querySelectorAll("th").forEach(th => {
//       headers.push(th.textContent.trim());
//     });
//     csv.push(headers);
//   }

//   // Variables for Sale-wise Profit totals
//   let totalSalePrice = 0;
//   let totalPurchasePrice = 0;
//   let totalProfitLoss = 0;
//   let validProfitPercentCount = 0;
//   let sumProfitPercent = 0;
//   let salePriceIdx = -1;
//   let purchasePriceIdx = -1;
//   let profitLossIdx = -1;
//   let profitPercentIdx = -1;

//   // Find column indices for Sale-wise Profit
//   if (activeReport === "Sale_wise_Profit") {
//     salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
//     purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
//     profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
//     profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));
//   }

//   // Extract data rows
//   const tbody = table.querySelector("tbody");
//   if (tbody) {
//     tbody.querySelectorAll("tr").forEach(tr => {
//       const row = [];
//       const cells = tr.querySelectorAll("td");
      
//       cells.forEach((td, idx) => {
//         let cellData = td.textContent.trim();
        
//         // Calculate totals for Sale-wise Profit
//         if (activeReport === "Sale_wise_Profit") {
//           const value = parseFloat(cellData.replace(/[^0-9.-]/g, ""));
//           if (!isNaN(value)) {
//             if (idx === salePriceIdx) totalSalePrice += value;
//             if (idx === purchasePriceIdx) totalPurchasePrice += value;
//             if (idx === profitLossIdx) totalProfitLoss += value;
//             if (idx === profitPercentIdx) {
//               sumProfitPercent += value;
//               validProfitPercentCount++;
//             }
//           }
//         }
        
//         // Escape quotes and wrap in quotes if contains comma
//         if (cellData.includes(",") || cellData.includes('"') || cellData.includes("\n")) {
//           cellData = '"' + cellData.replace(/"/g, '""') + '"';
//         }
//         row.push(cellData);
//       });
      
//       // Only add row if it's not the "no data" message
//       if (row.length > 0 && !row[0].includes("No records found") && !row[0].includes("Select a report")) {
//         csv.push(row);
//       }
//     });
//   }

//   // Add totals row for Sale-wise Profit
//   if (activeReport === "Sale_wise_Profit" && headers.length > 0) {
//     csv.push([]); // Empty row before totals
    
//     const totalsRow = new Array(headers.length).fill("");
//     totalsRow[0] = "TOTAL";
//     if (salePriceIdx >= 0) totalsRow[salePriceIdx] = totalSalePrice.toFixed(2);
//     if (purchasePriceIdx >= 0) totalsRow[purchasePriceIdx] = totalPurchasePrice.toFixed(2);
//     if (profitLossIdx >= 0) totalsRow[profitLossIdx] = totalProfitLoss.toFixed(2);
//     if (profitPercentIdx >= 0) {
//       const avgProfitPercent = validProfitPercentCount > 0 
//         ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
//         : "0.00";
//       totalsRow[profitPercentIdx] = avgProfitPercent + " (avg)";
//     }
    
//     csv.push(totalsRow);
//   }

//   // Convert to CSV string
//   const csvContent = csv.map(row => row.join(",")).join("\n");

//   // Create download link
//   const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
//   const link = document.createElement("a");
//   const url = URL.createObjectURL(blob);
  
//   link.setAttribute("href", url);
//   const filename = `${activeReport}_${new Date().toISOString().split("T")[0]}.csv`;
//   link.setAttribute("download", filename);
//   link.style.visibility = "hidden";
  
//   document.body.appendChild(link);
//   link.click();
//   document.body.removeChild(link);
// });



// // ==========================
// // 📊 Download Table as CSV - With Conditional Highlighting
// // ==========================
// $(document).on("click", "#download_csv", function () {
//   const activeBtn = $(".report-btn.active");
//   let activeReport = "Report";
//   let party = "";
//   let fromDate = "";
//   let toDate = "";

//   // Determine which report is active
//   if (activeBtn.attr("id") === "btn-ledger") {
//     activeReport = "Detailed_Ledger";
//     party = $("#search_name").val() || "All";
//     fromDate = $("#from_date").val() || "N/A";
//     toDate = $("#to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-cash-ledger") {
//     activeReport = "Cash_Ledger";
//     fromDate = $("#cash_from_date").val() || "N/A";
//     toDate = $("#cash_to_date").val() || "N/A";
//   } else if (activeBtn.attr("id") === "btn-trial") {
//     activeReport = "Trial_Balance";
//   } else if (activeBtn.attr("id") === "btn-sale") {
//     activeReport = "Sale_wise_Profit";
//     fromDate = $("#from_date").val() || "N/A";
//     toDate = $("#to_date").val() || "N/A";
//   }

//   // Get table data
//   const table = document.getElementById("reportTable");
//   if (!table || table.rows.length === 0) {
//     Swal.fire("No Data", "No data available to download.", "warning");
//     return;
//   }

//   let csv = [];
  
//   // Add metadata header
//   if (activeReport === "Detailed_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`Party: ${party}`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else if (activeReport === "Cash_Ledger") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else if (activeReport === "Sale_wise_Profit") {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([`From: ${fromDate}`, `To: ${toDate}`]);
//     csv.push([]); // Empty row
//   } else {
//     csv.push([`${activeReport.replace(/_/g, " ")} Report`]);
//     csv.push([]); // Empty row
//   }

//   // Extract headers
//   const headers = [];
//   const headerRow = table.querySelector("thead tr");
//   if (headerRow) {
//     headerRow.querySelectorAll("th").forEach(th => {
//       headers.push(th.textContent.trim());
//     });
//     csv.push(headers);
//   }

//   // Variables for Sale-wise Profit totals
//   let totalSalePrice = 0;
//   let totalPurchasePrice = 0;
//   let totalProfitLoss = 0;
//   let validProfitPercentCount = 0;
//   let sumProfitPercent = 0;
//   let salePriceIdx = -1;
//   let purchasePriceIdx = -1;
//   let profitLossIdx = -1;
//   let profitPercentIdx = -1;

//   // Find column indices for Sale-wise Profit
//   if (activeReport === "Sale_wise_Profit") {
//     salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
//     purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
//     profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
//     profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));
//   }

//   // Extract data rows
//   const tbody = table.querySelector("tbody");
//   if (tbody) {
//     tbody.querySelectorAll("tr").forEach(tr => {
//       const row = [];
//       const cells = tr.querySelectorAll("td");
      
//       // Variables for highlighting decision
//       let profitLossValue = null;
//       let purchasePriceValue = null;
//       let highlightType = ""; // "LOSS" or "PRICE_1" or ""
      
//       cells.forEach((td, idx) => {
//         let cellData = td.textContent.trim();
        
//         // Calculate totals for Sale-wise Profit
//         if (activeReport === "Sale_wise_Profit") {
//           const value = parseFloat(cellData.replace(/[^0-9.-]/g, ""));
//           if (!isNaN(value)) {
//             if (idx === salePriceIdx) totalSalePrice += value;
//             if (idx === purchasePriceIdx) {
//               totalPurchasePrice += value;
//               purchasePriceValue = value;
//             }
//             if (idx === profitLossIdx) {
//               totalProfitLoss += value;
//               profitLossValue = value;
//             }
//             if (idx === profitPercentIdx) {
//               sumProfitPercent += value;
//               validProfitPercentCount++;
//             }
//           }
//         }
        
//         // Escape quotes and wrap in quotes if contains comma
//         if (cellData.includes(",") || cellData.includes('"') || cellData.includes("\n")) {
//           cellData = '"' + cellData.replace(/"/g, '""') + '"';
//         }
//         row.push(cellData);
//       });
      
//       // Determine highlighting for Sale-wise Profit report
//       if (activeReport === "Sale_wise_Profit") {
//         // Priority: Loss (negative profit) gets RED flag
//         if (profitLossValue !== null && profitLossValue < 0) {
//           highlightType = "LOSS";
//         }
//         // Yellow flag for purchase price = 1 (only if not a loss)
//         else if (purchasePriceValue !== null && purchasePriceValue === 1) {
//           highlightType = "PRICE_1";
//         }
        
//         // Add flag at the end of the row
//         if (highlightType === "LOSS") {
//           row.push("[LOSS - RED]");
//         } else if (highlightType === "PRICE_1") {
//           row.push("[PRICE=1 - YELLOW]");
//         } else {
//           row.push(""); // Empty for normal rows
//         }
//       }
      
//       // Only add row if it's not the "no data" message
//       if (row.length > 0 && !row[0].includes("No records found") && !row[0].includes("Select a report")) {
//         csv.push(row);
//       }
//     });
//   }

//   // Add "Highlight Flag" header for Sale-wise Profit
//   if (activeReport === "Sale_wise_Profit" && headers.length > 0) {
//     // Update headers to include the flag column
//     const headerRowIndex = csv.findIndex(row => 
//       row.some(cell => cell.toLowerCase().includes("sale price") || cell.toLowerCase().includes("item name"))
//     );
//     if (headerRowIndex >= 0) {
//       csv[headerRowIndex].push("Highlight Flag");
//     }
//   }

//   // Add totals row for Sale-wise Profit
//   if (activeReport === "Sale_wise_Profit" && headers.length > 0) {
//     csv.push([]); // Empty row before totals
    
//     const totalsRow = new Array(headers.length).fill("");
//     totalsRow[0] = "TOTAL";
//     if (salePriceIdx >= 0) totalsRow[salePriceIdx] = totalSalePrice.toFixed(2);
//     if (purchasePriceIdx >= 0) totalsRow[purchasePriceIdx] = totalPurchasePrice.toFixed(2);
//     if (profitLossIdx >= 0) totalsRow[profitLossIdx] = totalProfitLoss.toFixed(2);
//     if (profitPercentIdx >= 0) {
//       const avgProfitPercent = validProfitPercentCount > 0 
//         ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
//         : "0.00";
//       totalsRow[profitPercentIdx] = avgProfitPercent + " (avg)";
//     }
//     totalsRow.push(""); // Empty flag for totals row
    
//     csv.push(totalsRow);
//   }

//   // Convert to CSV string
//   const csvContent = csv.map(row => row.join(",")).join("\n");

//   // Create download link
//   const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
//   const link = document.createElement("a");
//   const url = URL.createObjectURL(blob);
  
//   link.setAttribute("href", url);
//   const filename = `${activeReport}_${new Date().toISOString().split("T")[0]}.csv`;
//   link.setAttribute("download", filename);
//   link.style.visibility = "hidden";
  
//   document.body.appendChild(link);
//   link.click();
//   document.body.removeChild(link);
// });

// ==========================
// 📊 Download Table as Excel with Color Highlighting
// NOTE: This requires the ExcelJS library
// Include this in your HTML: <script src="https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.3.0/exceljs.min.js"></script>
// ==========================
$(document).on("click", "#download_csv", async function () {
  const activeBtn = $(".report-btn.active");
  let activeReport = "Report";
  let party = "";
  let fromDate = "";
  let toDate = "";

  // Determine which report is active
  if (activeBtn.attr("id") === "btn-ledger") {
    activeReport = "Detailed_Ledger";
    party = $("#search_name").val() || "All";
    fromDate = $("#from_date").val() || "N/A";
    toDate = $("#to_date").val() || "N/A";
  } else if (activeBtn.attr("id") === "btn-cash-ledger") {
    activeReport = "Cash_Ledger";
    fromDate = $("#cash_from_date").val() || "N/A";
    toDate = $("#cash_to_date").val() || "N/A";
  } else if (activeBtn.attr("id") === "btn-trial") {
    activeReport = "Trial_Balance";
  } else if (activeBtn.attr("id") === "btn-sale") {
    activeReport = "Sale_wise_Profit";
    fromDate = $("#from_date").val() || "N/A";
    toDate = $("#to_date").val() || "N/A";
  }

  // Get table data
  const table = document.getElementById("reportTable");
  if (!table || table.rows.length === 0) {
    Swal.fire("No Data", "No data available to download.", "warning");
    return;
  }

  // Check if ExcelJS is available
  if (typeof ExcelJS === 'undefined') {
    Swal.fire("Error", "Excel library not loaded. Please contact administrator.", "error");
    console.error("ExcelJS library is not loaded. Please include it in your HTML.");
    return;
  }

  // Create workbook and worksheet
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet(activeReport.substring(0, 31));

  let currentRow = 1;

  // Add metadata header
  if (activeReport === "Detailed_Ledger") {
    worksheet.addRow([`${activeReport.replace(/_/g, " ")} Report`]);
    worksheet.addRow([`Party: ${party}`]);
    worksheet.addRow([`From: ${fromDate}`, `To: ${toDate}`]);
    worksheet.addRow([]); // Empty row
    currentRow = 5;
  } else if (activeReport === "Cash_Ledger") {
    worksheet.addRow([`${activeReport.replace(/_/g, " ")} Report`]);
    worksheet.addRow([`From: ${fromDate}`, `To: ${toDate}`]);
    worksheet.addRow([]); // Empty row
    currentRow = 4;
  } else if (activeReport === "Sale_wise_Profit") {
    worksheet.addRow([`${activeReport.replace(/_/g, " ")} Report`]);
    worksheet.addRow([`From: ${fromDate}`, `To: ${toDate}`]);
    worksheet.addRow([]); // Empty row
    currentRow = 4;
  } else {
    worksheet.addRow([`${activeReport.replace(/_/g, " ")} Report`]);
    worksheet.addRow([]); // Empty row
    currentRow = 3;
  }

  // Extract headers
  const headers = [];
  const headerRow = table.querySelector("thead tr");
  if (headerRow) {
    headerRow.querySelectorAll("th").forEach(th => {
      headers.push(th.textContent.trim());
    });
    const excelHeaderRow = worksheet.addRow(headers);
    
    // Style header row
    excelHeaderRow.font = { bold: true };
    excelHeaderRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF198754' } // Green background
    };
    excelHeaderRow.font = { color: { argb: 'FFFFFFFF' }, bold: true }; // White text
    currentRow++;
  }

  // Variables for Sale-wise Profit totals
  let totalSalePrice = 0;
  let totalPurchasePrice = 0;
  let totalProfitLoss = 0;
  let validProfitPercentCount = 0;
  let sumProfitPercent = 0;
  let salePriceIdx = -1;
  let purchasePriceIdx = -1;
  let profitLossIdx = -1;
  let profitPercentIdx = -1;

  // Find column indices for Sale-wise Profit
  if (activeReport === "Sale_wise_Profit") {
    salePriceIdx = headers.findIndex(h => h.toLowerCase().includes("sale price"));
    purchasePriceIdx = headers.findIndex(h => h.toLowerCase().includes("purchase price"));
    profitLossIdx = headers.findIndex(h => h.toLowerCase().includes("profit") && h.toLowerCase().includes("loss") && !h.includes("%"));
    profitPercentIdx = headers.findIndex(h => h.includes("%") || h.toLowerCase().includes("percent"));
  }

  // Extract data rows
  const tbody = table.querySelector("tbody");
  if (tbody) {
    tbody.querySelectorAll("tr").forEach(tr => {
      const row = [];
      const cells = tr.querySelectorAll("td");
      
      // Variables for highlighting decision
      let profitLossValue = null;
      let purchasePriceValue = null;
      let highlightType = null;
      
      cells.forEach((td, idx) => {
        let cellData = td.textContent.trim();
        
        // Calculate totals for Sale-wise Profit
        if (activeReport === "Sale_wise_Profit") {
          const value = parseFloat(cellData.replace(/[^0-9.-]/g, ""));
          if (!isNaN(value)) {
            if (idx === salePriceIdx) totalSalePrice += value;
            if (idx === purchasePriceIdx) {
              totalPurchasePrice += value;
              purchasePriceValue = value;
            }
            if (idx === profitLossIdx) {
              totalProfitLoss += value;
              profitLossValue = value;
            }
            if (idx === profitPercentIdx) {
              sumProfitPercent += value;
              validProfitPercentCount++;
            }
          }
        }
        
        row.push(cellData);
      });
      
      // Only add row if it's not the "no data" message
      if (row.length > 0 && !row[0].includes("No records found") && !row[0].includes("Select a report")) {
        const excelRow = worksheet.addRow(row);
        
        // Determine highlighting for Sale-wise Profit report
        if (activeReport === "Sale_wise_Profit") {
          // Priority: Loss (negative profit) gets RED
          if (profitLossValue !== null && profitLossValue < 0) {
            highlightType = "LOSS";
          }
          // Yellow for purchase price = 1 (only if not a loss)
          else if (purchasePriceValue !== null && purchasePriceValue === 1) {
            highlightType = "PRICE_1";
          }

          // Apply highlighting to entire row
          if (highlightType === "LOSS") {
            excelRow.eachCell((cell) => {
              cell.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFFC7CE' } // Light red
              };
            });
          } else if (highlightType === "PRICE_1") {
            excelRow.eachCell((cell) => {
              cell.fill = {
                type: 'pattern',
                pattern: 'solid',
                fgColor: { argb: 'FFFFEB9C' } // Light yellow
              };
            });
          }
        }
        
        currentRow++;
      }
    });
  }

  // Add totals row for Sale-wise Profit
  if (activeReport === "Sale_wise_Profit" && headers.length > 0) {
    worksheet.addRow([]); // Empty row before totals
    
    const totalsRow = new Array(headers.length).fill("");
    totalsRow[0] = "TOTAL";
    if (salePriceIdx >= 0) totalsRow[salePriceIdx] = parseFloat(totalSalePrice.toFixed(2));
    if (purchasePriceIdx >= 0) totalsRow[purchasePriceIdx] = parseFloat(totalPurchasePrice.toFixed(2));
    if (profitLossIdx >= 0) totalsRow[profitLossIdx] = parseFloat(totalProfitLoss.toFixed(2));
    if (profitPercentIdx >= 0) {
      const avgProfitPercent = validProfitPercentCount > 0 
        ? (sumProfitPercent / validProfitPercentCount).toFixed(2) 
        : "0.00";
      totalsRow[profitPercentIdx] = avgProfitPercent + " (avg)";
    }
    
    const excelTotalsRow = worksheet.addRow(totalsRow);
    
    // Style totals row
    excelTotalsRow.font = { bold: true };
    excelTotalsRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFD3D3D3' } // Light gray
    };
  }

  // Auto-fit column widths
  worksheet.columns.forEach((column, index) => {
    let maxLength = 0;
    column.eachCell({ includeEmpty: true }, (cell) => {
      const cellLength = cell.value ? cell.value.toString().length : 10;
      if (cellLength > maxLength) {
        maxLength = cellLength;
      }
    });
    column.width = Math.min(maxLength + 2, 50); // Max width 50
  });

  // Generate Excel file
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], { 
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
  });
  
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  
  link.setAttribute("href", url);
  const filename = `${activeReport}_${new Date().toISOString().split("T")[0]}.xlsx`;
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
});