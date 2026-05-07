// /* ============================================================
//    MONTHLY REPORTS — monthly_reports.js
//    Two reports:
//      1. mprSelectReport('position') — Company Position / Standing
//      2. mprSelectReport('income')   — Monthly Income Statement
//    ============================================================ */

// 'use strict';

// // ── State ────────────────────────────────────────────────────────────────────
// let _mprCurrentReport = 'position';
// let _mprLastData      = null;   // raw JSON from server, for PDF

// // ── Utilities ────────────────────────────────────────────────────────────────
// function mprCSRF() {
//   for (const c of decodeURIComponent(document.cookie).split(';')) {
//     const t = c.trim();
//     if (t.startsWith('csrftoken=')) return t.slice('csrftoken='.length);
//   }
//   return '';
// }

// function mprFmt(num) {
//   if (num === null || num === undefined) return '—';
//   return new Intl.NumberFormat('en-PK', {
//     minimumFractionDigits: 2, maximumFractionDigits: 2
//   }).format(num);
// }

// function mprFmtDate(str) {
//   if (!str) return '—';
//   return new Date(str).toLocaleDateString('en-PK', {
//     day: '2-digit', month: 'short', year: 'numeric'
//   });
// }

// function mprMonthLabel(dateStr) {
//   return new Date(dateStr).toLocaleDateString('en-PK', { month: 'long', year: 'numeric' });
// }

// function mprLoader(msg = 'Generating report…') {
//   Swal.fire({ title: msg, didOpen: () => Swal.showLoading(), allowOutsideClick: false });
// }

// // ── Report selector ──────────────────────────────────────────────────────────
// function mprSelectReport(type) {
//   _mprCurrentReport = type;
//   document.querySelectorAll('.report-btn').forEach(b => b.classList.remove('active'));
//   document.getElementById('mpr-btn-' + type).classList.add('active');
//   document.getElementById('mpr-output').innerHTML = '';

//   if (type === 'position') {
//     mprRenderPositionForm();
//   } else {
//     mprRenderIncomeForm();
//   }
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  REPORT 1 — COMPANY POSITION
// // ─────────────────────────────────────────────────────────────────────────────

// function mprRenderPositionForm() {
//   // Default: last day of current month
//   const now   = new Date();
//   const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)
//                     .toISOString().split('T')[0];

//   document.getElementById('mpr-form-container').innerHTML = `
//     <div class="mpr-filter-card">
//       <div class="filter-field">
//         <label><i class="fa-regular fa-calendar"></i> As of Date</label>
//         <input type="date" id="mpr-as-of-date" value="${lastDay}">
//       </div>
//       <button class="mpr-generate-btn" onclick="mprFetchPosition()">
//         <i class="fa-solid fa-bolt"></i> Generate
//       </button>
//     </div>

//     <!-- Manual GST entries (NZ, AUS, etc.) -->
//     <div class="mpr-gst-section">
//       <h4><i class="fa-solid fa-plus-circle" style="margin-right:5px;color:var(--brand-primary);"></i>
//           Manual Receivables (GST / Foreign Amounts)</h4>
//       <div class="mpr-gst-rows" id="mpr-gst-rows">
//         <!-- pre-filled with the two common rows -->
//         <div class="mpr-gst-row">
//           <input type="text"   placeholder="Label (e.g. NEWZEALAND @2.12)"  value="NEWZEALAND">
//           <input type="number" placeholder="Amount (PKR)"  step="0.01" min="0" value="">
//           <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
//         </div>
//         <div class="mpr-gst-row">
//           <input type="text"   placeholder="Label (e.g. AUSTRALIA @2.4995)" value="AUSTRALIA">
//           <input type="number" placeholder="Amount (PKR)"  step="0.01" min="0" value="">
//           <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
//         </div>
//       </div>
//       <button class="mpr-gst-add-btn" onclick="mprAddGstRow()">
//         <i class="fa-solid fa-plus"></i> Add row
//       </button>
//     </div>
//   `;

//   // Auto-generate on load
//   mprFetchPosition();
// }

// function mprAddGstRow() {
//   const div = document.createElement('div');
//   div.className = 'mpr-gst-row';
//   div.innerHTML = `
//     <input type="text"   placeholder="Label">
//     <input type="number" placeholder="Amount (PKR)" step="0.01" min="0">
//     <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
//   `;
//   document.getElementById('mpr-gst-rows').appendChild(div);
// }

// function mprRemoveGst(btn) {
//   btn.closest('.mpr-gst-row').remove();
// }

// function mprCollectGstRows() {
//   const rows = [];
//   document.querySelectorAll('#mpr-gst-rows .mpr-gst-row').forEach(row => {
//     const label  = row.querySelector('input[type="text"]').value.trim();
//     const amount = parseFloat(row.querySelector('input[type="number"]').value) || 0;
//     if (label || amount) rows.push({ label: label || 'Other', amount });
//   });
//   return rows;
// }

// async function mprFetchPosition() {
//   const asOf = document.getElementById('mpr-as-of-date')?.value;
//   if (!asOf) { Swal.fire('Missing Date', 'Please pick an "As of Date".', 'warning'); return; }

//   mprLoader('Fetching company position…');

//   try {
//     const res  = await fetch('/accountsReports/monthly-position/', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json', 'X-CSRFToken': mprCSRF() },
//       body: JSON.stringify({ as_of_date: asOf })
//     });
//     const data = await res.json();
//     Swal.close();

//     if (data.error) { Swal.fire('Error', data.error, 'error'); return; }

//     const gstRows = mprCollectGstRows();
//     _mprLastData  = { ...data, gst_rows: gstRows, report_type: 'position' };
//     mprRenderPosition(data, gstRows);

//   } catch (e) {
//     Swal.close();
//     Swal.fire('Error', 'Could not fetch data. ' + e.message, 'error');
//   }
// }

// function mprRenderPosition(data, gstRows) {
//   // Compute totals
//   const stockWorth   = data.stock_worth || 0;
//   const cashBalance  = data.cash_balance || 0;
//   const partyRec     = data.total_party_receivable || 0;
//   const gstTotal     = gstRows.reduce((s, r) => s + (r.amount || 0), 0);
//   const totalAssets  = stockWorth + cashBalance + partyRec + gstTotal;
//   const totalPayable = data.total_payable || 0;
//   const netPosition  = totalAssets - totalPayable;
//   const isPositive   = netPosition >= 0;

//   // Receivables rows
//   const recRows = (data.receivables || []).map(r =>
//     `<tr><td>${r.name}</td><td>${mprFmt(r.balance)}</td></tr>`
//   ).join('');

//   // GST rows HTML
//   const gstHtml = gstRows.map(r =>
//     `<tr><td>${r.label}</td><td>${mprFmt(r.amount)}</td></tr>`
//   ).join('');

//   // Payables rows
//   const payRows = (data.payables || []).map(r =>
//     `<tr><td>${r.name}</td><td>${mprFmt(r.balance)}</td></tr>`
//   ).join('');

//   document.getElementById('mpr-output').innerHTML = `
//     <!-- Toolbar -->
//     <div class="mpr-toolbar">
//       <button class="mpr-toolbar-btn mpr-btn-print" onclick="mprPrintPosition()">
//         <i class="fa-solid fa-print"></i> Print
//       </button>
//       <button class="mpr-toolbar-btn mpr-btn-pdf" onclick="mprPdfPosition()">
//         <i class="fa-solid fa-file-pdf"></i> PDF
//       </button>
//     </div>

//     <!-- Report card -->
//     <div class="mpr-report-card" id="mpr-position-card">
//       <p class="mpr-report-title">Company Position</p>
//       <p class="mpr-report-subtitle">As of ${mprFmtDate(data.as_of_date)}</p>

//       <div class="mpr-position-grid">

//         <!-- ASSETS column -->
//         <div>
//           <div class="mpr-col-header mpr-assets">Assets / Receivables</div>
//           <table class="mpr-breakdown-table">
//             <tr class="mpr-section-header"><td colspan="2">Stock</td></tr>
//             <tr><td>Total Stock Worth</td><td>${mprFmt(stockWorth)}</td></tr>

//             <tr class="mpr-section-header"><td colspan="2">Party Receivables</td></tr>
//             ${recRows}

//             ${gstRows.length ? `
//             <tr class="mpr-section-header"><td colspan="2">GST / Foreign Receivables</td></tr>
//             ${gstHtml}
//             ` : ''}

//             <tr class="mpr-section-header"><td colspan="2">Cash</td></tr>
//             <tr><td>Cash Balance</td><td>${mprFmt(cashBalance)}</td></tr>

//             <tr class="mpr-subtotal">
//               <td>TOTAL RECEIVABLE</td>
//               <td>${mprFmt(totalAssets)}</td>
//             </tr>
//           </table>
//         </div>

//         <!-- LIABILITIES column -->
//         <div>
//           <div class="mpr-col-header mpr-liab">Liabilities / Payables</div>
//           <table class="mpr-breakdown-table">
//             <tr class="mpr-section-header"><td colspan="2">Party Payables</td></tr>
//             ${payRows}
//             <tr class="mpr-subtotal">
//               <td>TOTAL PAYABLE</td>
//               <td>${mprFmt(totalPayable)}</td>
//             </tr>
//           </table>
//         </div>

//       </div>

//       <!-- Net position bar -->
//       <div class="mpr-net-bar ${isPositive ? '' : 'mpr-negative'}">
//         <span class="mpr-net-label">Net Company Position</span>
//         <span class="mpr-net-value">${isPositive ? '' : '('}${mprFmt(Math.abs(netPosition))}${isPositive ? '' : ')'}</span>
//       </div>
//     </div>
//   `;
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  REPORT 2 — INCOME STATEMENT
// // ─────────────────────────────────────────────────────────────────────────────

// function mprRenderIncomeForm() {
//   const now       = new Date();
//   const fromDate  = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
//   const toDate    = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];

//   document.getElementById('mpr-form-container').innerHTML = `
//     <div class="mpr-filter-card">
//       <div class="filter-field">
//         <label><i class="fa-regular fa-calendar"></i> From Date</label>
//         <input type="date" id="mpr-from-date" value="${fromDate}">
//       </div>
//       <div class="filter-field">
//         <label><i class="fa-regular fa-calendar"></i> To Date</label>
//         <input type="date" id="mpr-to-date" value="${toDate}">
//       </div>
//       <button class="mpr-generate-btn" onclick="mprFetchIncome()">
//         <i class="fa-solid fa-bolt"></i> Generate
//       </button>
//     </div>
//   `;

//   mprFetchIncome();
// }

// async function mprFetchIncome() {
//   const from = document.getElementById('mpr-from-date')?.value;
//   const to   = document.getElementById('mpr-to-date')?.value;
//   if (!from || !to) { Swal.fire('Missing Dates', 'Please fill in both dates.', 'warning'); return; }

//   mprLoader('Fetching income statement…');

//   try {
//     const res  = await fetch('/accountsReports/monthly-income/', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json', 'X-CSRFToken': mprCSRF() },
//       body: JSON.stringify({ from_date: from, to_date: to })
//     });
//     const data = await res.json();
//     Swal.close();

//     if (data.error) { Swal.fire('Error', data.error, 'error'); return; }

//     _mprLastData = { ...data, report_type: 'income' };
//     mprRenderIncome(data);

//   } catch (e) {
//     Swal.close();
//     Swal.fire('Error', 'Could not fetch data. ' + e.message, 'error');
//   }
// }

// function mprRenderIncome(data) {
//   const isProfit = data.net_income >= 0;

//   const expenseRows = (data.expenses || []).map(e =>
//     `<tr><td>${e.category}</td><td>${mprFmt(e.amount)}</td></tr>`
//   ).join('') || `<tr><td colspan="2" style="color:var(--text-tertiary);text-align:center;">No expenses recorded</td></tr>`;

//   const monthLabel = mprFmtDate(data.from_date) + ' – ' + mprFmtDate(data.to_date);

//   document.getElementById('mpr-output').innerHTML = `
//     <!-- Toolbar -->
//     <div class="mpr-toolbar">
//       <button class="mpr-toolbar-btn mpr-btn-print" onclick="mprPrintIncome()">
//         <i class="fa-solid fa-print"></i> Print
//       </button>
//       <button class="mpr-toolbar-btn mpr-btn-pdf" onclick="mprPdfIncome()">
//         <i class="fa-solid fa-file-pdf"></i> PDF
//       </button>
//     </div>

//     <div class="mpr-report-card" id="mpr-income-card">
//       <p class="mpr-report-title">Income Statement</p>
//       <p class="mpr-report-subtitle">${monthLabel}</p>

//       <div class="mpr-income-block">

//         <!-- Revenue section -->
//         <div class="mpr-income-section">
//           <div class="mpr-income-section-title">Revenues</div>
//           <table class="mpr-income-table">
//             <tr><td>Gross Sales Revenue</td><td>${mprFmt(data.gross_revenue)}</td></tr>
//             <tr><td>Less: Sales Returns</td><td class="mpr-red">(${mprFmt(data.sales_returns)})</td></tr>
//             <tr class="mpr-total-row"><td>Net Revenue</td><td>${mprFmt(data.net_revenue)}</td></tr>
//           </table>
//         </div>

//         <!-- COGS section -->
//         <div class="mpr-income-section">
//           <div class="mpr-income-section-title">Cost of Sales</div>
//           <table class="mpr-income-table">
//             <tr><td>Cost of Goods Sold</td><td>${mprFmt(data.cogs)}</td></tr>
//             <tr class="mpr-total-row">
//               <td>Gross Profit</td>
//               <td class="${data.gross_profit >= 0 ? 'mpr-green' : 'mpr-red'}">${mprFmt(data.gross_profit)}</td>
//             </tr>
//           </table>
//         </div>

//         <!-- Expenses section -->
//         <div class="mpr-income-section">
//           <div class="mpr-income-section-title">Expenses</div>
//           <table class="mpr-income-table">
//             ${expenseRows}
//             <tr class="mpr-total-row"><td>Total Expenses</td><td class="mpr-red">${mprFmt(data.total_expenses)}</td></tr>
//           </table>
//         </div>

//         <!-- Net income banner -->
//         <div class="mpr-income-banner ${isProfit ? '' : 'mpr-loss'}">
//           <span class="mpr-income-banner-label">${isProfit ? 'Net Income' : 'Net Loss'}</span>
//           <span class="mpr-income-banner-value">
//             ${isProfit ? '' : '('}${mprFmt(Math.abs(data.net_income))}${isProfit ? '' : ')'}
//           </span>
//         </div>

//       </div>
//     </div>
//   `;
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  PDF — Company Position
// // ─────────────────────────────────────────────────────────────────────────────
// function mprPdfPosition() {
//   if (!_mprLastData || _mprLastData.report_type !== 'position') {
//     Swal.fire('No Data', 'Generate the report first.', 'info'); return;
//   }
//   const d       = _mprLastData;
//   const gstRows = d.gst_rows || [];
//   const stockWorth  = d.stock_worth   || 0;
//   const cashBalance = d.cash_balance  || 0;
//   const partyRec    = d.total_party_receivable || 0;
//   const gstTotal    = gstRows.reduce((s,r) => s + (r.amount||0), 0);
//   const totalAssets = stockWorth + cashBalance + partyRec + gstTotal;
//   const totalPay    = d.total_payable || 0;
//   const net         = totalAssets - totalPay;

//   const { jsPDF } = window.jspdf;
//   const doc  = new jsPDF('p','pt','a4');
//   const pW   = doc.internal.pageSize.width;
//   const pH   = doc.internal.pageSize.height;
//   const today = new Date().toLocaleDateString('en-PK',{day:'2-digit',month:'short',year:'numeric'});

//   function drawHeader() {
//     doc.setFillColor(5,150,105); doc.rect(0,0,pW,36,'F');
//     doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(255,255,255);
//     doc.text('Financee', 28, 23);
//     doc.setFont('helvetica','normal'); doc.setFontSize(9);
//     doc.text('Company Position Report', pW-28, 23, {align:'right'});
//     doc.setFillColor(240,253,244); doc.rect(0,36,pW,22,'F');
//     doc.setFont('helvetica','italic'); doc.setFontSize(8); doc.setTextColor(100,116,139);
//     doc.text(`As of: ${mprFmtDate(d.as_of_date)}`, 28, 51);
//     doc.text(`Generated: ${today}`, pW-28, 51, {align:'right'});
//     doc.setDrawColor(209,250,229); doc.setLineWidth(0.5); doc.line(0,58,pW,58);
//   }

//   drawHeader();
//   let y = 72;

//   function section(title, rows, isTotals) {
//     doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(100,116,139);
//     doc.text(title.toUpperCase(), 28, y); y += 14;
//     rows.forEach(([label, amount]) => {
//       doc.setFont('helvetica', isTotals ? 'bold' : 'normal');
//       doc.setFontSize(8.5); doc.setTextColor(30,41,59);
//       doc.text(label, 36, y);
//       doc.text(mprFmt(amount), pW-28, y, {align:'right'});
//       y += 13;
//     });
//     y += 4;
//   }

//   // Receivables
//   section('STOCK', [['Total Stock Worth', stockWorth]]);
//   section('PARTY RECEIVABLES', (d.receivables||[]).map(r=>[r.name, r.balance]));
//   if (gstRows.length) section('GST / FOREIGN RECEIVABLES', gstRows.map(r=>[r.label, r.amount]));
//   section('CASH', [['Cash Balance', cashBalance]]);

//   doc.setDrawColor(209,250,229); doc.setLineWidth(1); doc.line(28,y,pW-28,y); y+=8;
//   doc.setFont('helvetica','bold'); doc.setFontSize(9.5); doc.setTextColor(5,150,105);
//   doc.text('TOTAL RECEIVABLE', 28, y);
//   doc.text(mprFmt(totalAssets), pW-28, y, {align:'right'}); y+=20;

//   // Payables
//   section('PARTY PAYABLES', (d.payables||[]).map(r=>[r.name, r.balance]));
//   doc.setDrawColor(252,165,165); doc.setLineWidth(1); doc.line(28,y,pW-28,y); y+=8;
//   doc.setFont('helvetica','bold'); doc.setFontSize(9.5); doc.setTextColor(220,38,38);
//   doc.text('TOTAL PAYABLE', 28, y);
//   doc.text(mprFmt(totalPay), pW-28, y, {align:'right'}); y+=22;

//   // Net
//   const posColor = net >= 0 ? [5,150,105] : [220,38,38];
//   doc.setFillColor(...posColor, 15); doc.roundedRect(28,y,pW-56,32,4,4,'F');
//   doc.setFont('helvetica','bold'); doc.setFontSize(11); doc.setTextColor(...posColor);
//   doc.text('Net Company Position', 40, y+21);
//   doc.text(mprFmt(Math.abs(net)), pW-40, y+21, {align:'right'});

//   doc.save(`Company_Position_${d.as_of_date}.pdf`);
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  PDF — Income Statement
// // ─────────────────────────────────────────────────────────────────────────────
// function mprPdfIncome() {
//   if (!_mprLastData || _mprLastData.report_type !== 'income') {
//     Swal.fire('No Data', 'Generate the report first.', 'info'); return;
//   }
//   const d = _mprLastData;
//   const { jsPDF } = window.jspdf;
//   const doc = new jsPDF('p','pt','a4');
//   const pW  = doc.internal.pageSize.width;
//   const today = new Date().toLocaleDateString('en-PK',{day:'2-digit',month:'short',year:'numeric'});

//   function drawHeader() {
//     doc.setFillColor(5,150,105); doc.rect(0,0,pW,36,'F');
//     doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(255,255,255);
//     doc.text('Financee', 28, 23);
//     doc.setFont('helvetica','normal'); doc.setFontSize(9);
//     doc.text('Income Statement', pW-28, 23, {align:'right'});
//     doc.setFillColor(240,253,244); doc.rect(0,36,pW,22,'F');
//     doc.setFont('helvetica','italic'); doc.setFontSize(8); doc.setTextColor(100,116,139);
//     doc.text(`${mprFmtDate(d.from_date)} – ${mprFmtDate(d.to_date)}`, 28, 51);
//     doc.text(`Generated: ${today}`, pW-28, 51, {align:'right'});
//     doc.setDrawColor(209,250,229); doc.setLineWidth(0.5); doc.line(0,58,pW,58);
//   }

//   drawHeader();

//   const rows = [
//     ['Gross Sales Revenue', mprFmt(d.gross_revenue)],
//     ['Less: Sales Returns', `(${mprFmt(d.sales_returns)})`],
//     ['Net Revenue', mprFmt(d.net_revenue)],
//     ['', ''],
//     ['Cost of Goods Sold', mprFmt(d.cogs)],
//     ['Gross Profit', mprFmt(d.gross_profit)],
//     ['', ''],
//     ...(d.expenses||[]).map(e => [e.category, mprFmt(e.amount)]),
//     ['Total Expenses', mprFmt(d.total_expenses)],
//     ['', ''],
//     [d.net_income >= 0 ? 'NET INCOME' : 'NET LOSS', mprFmt(Math.abs(d.net_income))],
//   ];

//   doc.autoTable({
//     startY: 70,
//     margin: { left: 28, right: 28 },
//     head: [['Description', 'Amount (PKR)']],
//     body: rows,
//     theme: 'grid',
//     headStyles: { fillColor: [5,150,105], textColor:[255,255,255], fontStyle:'bold', fontSize:8.5 },
//     bodyStyles: { fontSize: 8.5, textColor:[30,41,59] },
//     columnStyles: { 1: { halign:'right', fontStyle:'bold' } },
//     didParseCell: (data) => {
//       if (data.row.index === rows.length - 1) {
//         data.cell.styles.fontStyle = 'bold';
//         data.cell.styles.fillColor = d.net_income >= 0 ? [240,253,244] : [255,241,242];
//         data.cell.styles.textColor = d.net_income >= 0 ? [5,150,105] : [220,38,38];
//       }
//     }
//   });

//   doc.save(`Income_Statement_${d.from_date}_to_${d.to_date}.pdf`);
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  Print helpers (browser print)
// // ─────────────────────────────────────────────────────────────────────────────
// function mprPrintPosition() {
//   const el = document.getElementById('mpr-position-card');
//   if (!el) { Swal.fire('No Data', 'Generate the report first.', 'info'); return; }
//   mprPrintElement(el, 'Company Position');
// }

// function mprPrintIncome() {
//   const el = document.getElementById('mpr-income-card');
//   if (!el) { Swal.fire('No Data', 'Generate the report first.', 'info'); return; }
//   mprPrintElement(el, 'Income Statement');
// }

// function mprPrintElement(el, title) {
//   const win = window.open('', '_blank', 'width=900,height=700');
//   win.document.write(`<!DOCTYPE html><html><head>
//     <title>${title}</title>
//     <style>
//       body{font-family:system-ui,sans-serif;padding:24px;color:#1e293b;}
//       table{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:12px;}
//       td{padding:6px 8px;border-bottom:1px solid #e2e8f0;}
//       td:last-child{text-align:right;font-weight:600;}
//       .mpr-col-header{font-size:11px;font-weight:700;text-transform:uppercase;
//         letter-spacing:.08em;padding-bottom:4px;border-bottom:2px solid #059669;
//         color:#059669;margin-bottom:6px;}
//       .mpr-col-header.mpr-liab{border-color:#dc2626;color:#dc2626;}
//       .mpr-position-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:20px;}
//       .mpr-net-bar,.mpr-income-banner{background:#f0fdf4;border:2px solid #6ee7b7;
//         border-radius:8px;padding:16px 20px;display:flex;justify-content:space-between;
//         align-items:center;margin-top:8px;}
//       .mpr-net-bar.mpr-negative,.mpr-income-banner.mpr-loss{background:#fff1f2;border-color:#fca5a5;}
//       .mpr-net-value,.mpr-income-banner-value{font-size:22px;font-weight:800;color:#059669;}
//       .mpr-net-bar.mpr-negative .mpr-net-value,
//       .mpr-income-banner.mpr-loss .mpr-income-banner-value{color:#dc2626;}
//       .mpr-section-header td{font-size:11px;font-weight:700;text-transform:uppercase;
//         color:#64748b;background:#f8fafc;border-bottom:none;padding-top:14px;}
//       .mpr-subtotal td{font-weight:700;border-top:2px solid #e2e8f0;border-bottom:none;}
//       .mpr-subtotal td:last-child{color:#059669;}
//       .mpr-income-section{border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:10px;}
//       .mpr-income-section-title{font-size:11px;font-weight:700;text-transform:uppercase;
//         padding:6px 10px;background:#f8fafc;color:#64748b;border-bottom:1px solid #e2e8f0;}
//       .mpr-total-row td{font-weight:700;background:#f8fafc;}
//       .mpr-green{color:#059669!important;} .mpr-red{color:#dc2626!important;}
//       h1{font-size:16px;margin:0 0 2px;} .subtitle{font-size:12px;color:#64748b;margin:0 0 20px;}
//     </style>
//   </head><body>
//     <h1>${title}</h1>
//     ${el.querySelector('.mpr-report-subtitle') ? `<p class="subtitle">${el.querySelector('.mpr-report-subtitle').textContent}</p>` : ''}
//     ${el.innerHTML}
//   </body></html>`);
//   win.document.close();
//   win.focus();
//   setTimeout(() => { win.print(); }, 400);
// }

// // ─────────────────────────────────────────────────────────────────────────────
// //  Init
// // ─────────────────────────────────────────────────────────────────────────────
// document.addEventListener('DOMContentLoaded', () => {
//   mprSelectReport('position');
// });


/* ============================================================
   MONTHLY REPORTS — monthly_reports.js
   Two reports:
     1. mprSelectReport('position') — Company Position / Standing
     2. mprSelectReport('income')   — Monthly Income Statement
   ============================================================ */

'use strict';

// ── State ────────────────────────────────────────────────────────────────────
let _mprCurrentReport = 'position';
let _mprLastData      = null;   // raw JSON from server, for PDF

// ── Utilities ────────────────────────────────────────────────────────────────
function mprCSRF() {
  for (const c of decodeURIComponent(document.cookie).split(';')) {
    const t = c.trim();
    if (t.startsWith('csrftoken=')) return t.slice('csrftoken='.length);
  }
  return '';
}

function mprFmt(num) {
  if (num === null || num === undefined) return '—';
  return new Intl.NumberFormat('en-PK', {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  }).format(num);
}

function mprFmtDate(str) {
  if (!str) return '—';
  return new Date(str).toLocaleDateString('en-PK', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

function mprMonthLabel(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-PK', { month: 'long', year: 'numeric' });
}

function mprLoader(msg = 'Generating report…') {
  Swal.fire({ title: msg, didOpen: () => Swal.showLoading(), allowOutsideClick: false });
}

// ── Report selector ──────────────────────────────────────────────────────────
function mprSelectReport(type) {
  _mprCurrentReport = type;
  document.querySelectorAll('.report-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('mpr-btn-' + type).classList.add('active');
  document.getElementById('mpr-output').innerHTML = '';

  if (type === 'position') {
    mprRenderPositionForm();
  } else {
    mprRenderIncomeForm();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  REPORT 1 — COMPANY POSITION
// ─────────────────────────────────────────────────────────────────────────────

function mprRenderPositionForm() {
  // Default: last day of current month
  const now   = new Date();
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)
                    .toISOString().split('T')[0];

  document.getElementById('mpr-form-container').innerHTML = `
    <div class="mpr-filter-card">
      <div class="filter-field">
        <label><i class="fa-regular fa-calendar"></i> As of Date</label>
        <input type="date" id="mpr-as-of-date" value="${lastDay}">
      </div>
      <button class="mpr-generate-btn" onclick="mprFetchPosition()">
        <i class="fa-solid fa-bolt"></i> Generate
      </button>
    </div>

    <!-- Manual GST entries (NZ, AUS, etc.) -->
    <div class="mpr-gst-section">
      <h4><i class="fa-solid fa-plus-circle" style="margin-right:5px;color:var(--brand-primary);"></i>
          Manual Receivables (GST / Foreign Amounts)</h4>
      <div class="mpr-gst-rows" id="mpr-gst-rows">
        <!-- pre-filled with the two common rows -->
        <div class="mpr-gst-row">
          <input type="text"   placeholder="Label (e.g. NEWZEALAND @2.12)"  value="NEWZEALAND">
          <input type="number" placeholder="Amount (PKR)"  step="0.01" min="0" value="">
          <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
        </div>
        <div class="mpr-gst-row">
          <input type="text"   placeholder="Label (e.g. AUSTRALIA @2.4995)" value="AUSTRALIA">
          <input type="number" placeholder="Amount (PKR)"  step="0.01" min="0" value="">
          <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
        </div>
      </div>
      <button class="mpr-gst-add-btn" onclick="mprAddGstRow()">
        <i class="fa-solid fa-plus"></i> Add row
      </button>
    </div>
  `;

  // Auto-generate on load
  mprFetchPosition();
}

function mprAddGstRow() {
  const div = document.createElement('div');
  div.className = 'mpr-gst-row';
  div.innerHTML = `
    <input type="text"   placeholder="Label">
    <input type="number" placeholder="Amount (PKR)" step="0.01" min="0">
    <button class="mpr-gst-remove" onclick="mprRemoveGst(this)" title="Remove">×</button>
  `;
  document.getElementById('mpr-gst-rows').appendChild(div);
}

function mprRemoveGst(btn) {
  btn.closest('.mpr-gst-row').remove();
}

function mprCollectGstRows() {
  const rows = [];
  document.querySelectorAll('#mpr-gst-rows .mpr-gst-row').forEach(row => {
    const label  = row.querySelector('input[type="text"]').value.trim();
    const amount = parseFloat(row.querySelector('input[type="number"]').value) || 0;
    if (label || amount) rows.push({ label: label || 'Other', amount });
  });
  return rows;
}

async function mprFetchPosition() {
  const asOf = document.getElementById('mpr-as-of-date')?.value;
  if (!asOf) { Swal.fire('Missing Date', 'Please pick an "As of Date".', 'warning'); return; }

  mprLoader('Fetching company position…');

  try {
    const res  = await fetch('/accountsReports/monthly-position/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': mprCSRF() },
      body: JSON.stringify({ as_of_date: asOf })
    });
    const data = await res.json();
    Swal.close();

    if (data.error) { Swal.fire('Error', data.error, 'error'); return; }

    const gstRows = mprCollectGstRows();
    _mprLastData  = { ...data, gst_rows: gstRows, report_type: 'position' };
    mprRenderPosition(data, gstRows);

  } catch (e) {
    Swal.close();
    Swal.fire('Error', 'Could not fetch data. ' + e.message, 'error');
  }
}

function mprRenderPosition(data, gstRows) {
  // Compute totals
  const stockWorth   = data.stock_worth || 0;
  const cashBalance  = data.cash_balance || 0;
  const partyRec     = data.total_party_receivable || 0;
  const gstTotal     = gstRows.reduce((s, r) => s + (r.amount || 0), 0);
  const totalAssets  = stockWorth + cashBalance + partyRec + gstTotal;
  const totalPayable = data.total_payable || 0;
  const netPosition  = totalAssets - totalPayable;
  const isPositive   = netPosition >= 0;

  // Receivables rows
  const recRows = (data.receivables || []).map(r =>
    `<tr><td>${r.name}</td><td>${mprFmt(r.balance)}</td></tr>`
  ).join('');

  // GST rows HTML
  const gstHtml = gstRows.map(r =>
    `<tr><td>${r.label}</td><td>${mprFmt(r.amount)}</td></tr>`
  ).join('');

  // Payables rows
  const payRows = (data.payables || []).map(r =>
    `<tr><td>${r.name}</td><td>${mprFmt(r.balance)}</td></tr>`
  ).join('');

  document.getElementById('mpr-output').innerHTML = `
    <!-- Toolbar -->
    <div class="mpr-toolbar">
      <button class="mpr-toolbar-btn mpr-btn-print" onclick="mprPrintPosition()">
        <i class="fa-solid fa-print"></i> Print
      </button>
      <button class="mpr-toolbar-btn mpr-btn-pdf" onclick="mprPdfPosition()">
        <i class="fa-solid fa-file-pdf"></i> PDF
      </button>
    </div>

    <!-- Report card -->
    <div class="mpr-report-card" id="mpr-position-card">
      <p class="mpr-report-title">Company Position</p>
      <p class="mpr-report-subtitle">As of ${mprFmtDate(data.as_of_date)}</p>

      <div class="mpr-position-grid">

        <!-- ASSETS column -->
        <div>
          <div class="mpr-col-header mpr-assets">Assets / Receivables</div>
          <table class="mpr-breakdown-table">
            <tr class="mpr-section-header"><td colspan="2">Stock</td></tr>
            <tr><td>Total Stock Worth</td><td>${mprFmt(stockWorth)}</td></tr>

            <tr class="mpr-section-header"><td colspan="2">Party Receivables</td></tr>
            ${recRows}

            ${gstRows.length ? `
            <tr class="mpr-section-header"><td colspan="2">GST / Foreign Receivables</td></tr>
            ${gstHtml}
            ` : ''}

            <tr class="mpr-section-header"><td colspan="2">Cash</td></tr>
            <tr><td>Cash Balance</td><td>${mprFmt(cashBalance)}</td></tr>

            <tr class="mpr-subtotal">
              <td>TOTAL RECEIVABLE</td>
              <td>${mprFmt(totalAssets)}</td>
            </tr>
          </table>
        </div>

        <!-- LIABILITIES column -->
        <div>
          <div class="mpr-col-header mpr-liab">Liabilities / Payables</div>
          <table class="mpr-breakdown-table">
            <tr class="mpr-section-header"><td colspan="2">Party Payables</td></tr>
            ${payRows}
            <tr class="mpr-subtotal">
              <td>TOTAL PAYABLE</td>
              <td>${mprFmt(totalPayable)}</td>
            </tr>
          </table>
        </div>

      </div>

      <!-- Net position bar -->
      <div class="mpr-net-bar ${isPositive ? '' : 'mpr-negative'}">
        <span class="mpr-net-label">Net Company Position</span>
        <span class="mpr-net-value">${isPositive ? '' : '('}${mprFmt(Math.abs(netPosition))}${isPositive ? '' : ')'}</span>
      </div>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
//  REPORT 2 — INCOME STATEMENT
// ─────────────────────────────────────────────────────────────────────────────

function mprRenderIncomeForm() {
  const now       = new Date();
  const fromDate  = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
  const toDate    = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];

  document.getElementById('mpr-form-container').innerHTML = `
    <div class="mpr-filter-card">
      <div class="filter-field">
        <label><i class="fa-regular fa-calendar"></i> From Date</label>
        <input type="date" id="mpr-from-date" value="${fromDate}">
      </div>
      <div class="filter-field">
        <label><i class="fa-regular fa-calendar"></i> To Date</label>
        <input type="date" id="mpr-to-date" value="${toDate}">
      </div>
      <div class="filter-field">
        <label><i class="fa-solid fa-coins"></i> Sales Revenue (PKR)</label>
        <input type="number" id="mpr-sales-revenue" placeholder="0.00" step="0.01" min="0"
               style="width:160px;">
      </div>
      <div class="filter-field">
        <label><i class="fa-solid fa-boxes-stacked"></i> Cost of Goods Sold (PKR)</label>
        <input type="number" id="mpr-cogs" placeholder="0.00" step="0.01" min="0"
               style="width:160px;">
      </div>
      <button class="mpr-generate-btn" onclick="mprFetchIncome()">
        <i class="fa-solid fa-bolt"></i> Generate
      </button>
    </div>
  `;
}

async function mprFetchIncome() {
  const from    = document.getElementById('mpr-from-date')?.value;
  const to      = document.getElementById('mpr-to-date')?.value;
  const revenue = document.getElementById('mpr-sales-revenue')?.value;
  const cogs    = document.getElementById('mpr-cogs')?.value;

  if (!from || !to) {
    Swal.fire('Missing Dates', 'Please fill in both dates.', 'warning'); return;
  }
  if (revenue === '' || revenue === null || revenue === undefined) {
    Swal.fire('Missing Value', 'Please enter the Sales Revenue.', 'warning'); return;
  }
  if (cogs === '' || cogs === null || cogs === undefined) {
    Swal.fire('Missing Value', 'Please enter the Cost of Goods Sold.', 'warning'); return;
  }

  mprLoader('Fetching income statement…');

  try {
    const res  = await fetch('/accountsReports/monthly-income/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': mprCSRF() },
      body: JSON.stringify({
        from_date:     from,
        to_date:       to,
        sales_revenue: parseFloat(revenue),
        cogs:          parseFloat(cogs)
      })
    });
    const data = await res.json();
    Swal.close();

    if (data.error) { Swal.fire('Error', data.error, 'error'); return; }

    _mprLastData = { ...data, report_type: 'income' };
    mprRenderIncome(data);

  } catch (e) {
    Swal.close();
    Swal.fire('Error', 'Could not fetch data. ' + e.message, 'error');
  }
}

function mprRenderIncome(data) {
  const isProfit = data.net_income >= 0;

  const expenseRows = (data.expenses || []).map(e =>
    `<tr><td>${e.category}</td><td>${mprFmt(e.amount)}</td></tr>`
  ).join('') || `<tr><td colspan="2" style="color:var(--text-tertiary);text-align:center;font-size:0.8rem;padding:12px;">No operating expenses recorded in this period</td></tr>`;

  const monthLabel = mprFmtDate(data.from_date) + ' – ' + mprFmtDate(data.to_date);

  document.getElementById('mpr-output').innerHTML = `
    <!-- Toolbar -->
    <div class="mpr-toolbar">
      <button class="mpr-toolbar-btn mpr-btn-print" onclick="mprPrintIncome()">
        <i class="fa-solid fa-print"></i> Print
      </button>
      <button class="mpr-toolbar-btn mpr-btn-pdf" onclick="mprPdfIncome()">
        <i class="fa-solid fa-file-pdf"></i> PDF
      </button>
    </div>

    <div class="mpr-report-card" id="mpr-income-card">
      <p class="mpr-report-title">Income Statement</p>
      <p class="mpr-report-subtitle">${monthLabel}</p>

      <div class="mpr-income-block">

        <!-- Revenue & COGS -->
        <div class="mpr-income-section">
          <div class="mpr-income-section-title">Revenue &amp; Cost of Sales</div>
          <table class="mpr-income-table">
            <tr><td>Sales Revenue</td><td>${mprFmt(data.sales_revenue)}</td></tr>
            <tr><td>Less: Cost of Goods Sold</td><td class="mpr-red">(${mprFmt(data.cogs)})</td></tr>
            <tr class="mpr-total-row">
              <td>Gross Profit</td>
              <td class="${data.gross_profit >= 0 ? 'mpr-green' : 'mpr-red'}">${mprFmt(data.gross_profit)}</td>
            </tr>
          </table>
        </div>

        <!-- Operating Expenses -->
        <div class="mpr-income-section">
          <div class="mpr-income-section-title">Operating Expenses</div>
          <table class="mpr-income-table">
            ${expenseRows}
            <tr class="mpr-total-row">
              <td>Total Expenses</td>
              <td class="mpr-red">(${mprFmt(data.total_expenses)})</td>
            </tr>
          </table>
        </div>

        <!-- Net income banner -->
        <div class="mpr-income-banner ${isProfit ? '' : 'mpr-loss'}">
          <span class="mpr-income-banner-label">${isProfit ? 'Net Income' : 'Net Loss'}</span>
          <span class="mpr-income-banner-value">
            ${isProfit ? '' : '('}${mprFmt(Math.abs(data.net_income))}${isProfit ? '' : ')'}
          </span>
        </div>

      </div>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
//  PDF — Company Position
// ─────────────────────────────────────────────────────────────────────────────
function mprPdfPosition() {
  if (!_mprLastData || _mprLastData.report_type !== 'position') {
    Swal.fire('No Data', 'Generate the report first.', 'info'); return;
  }
  const d       = _mprLastData;
  const gstRows = d.gst_rows || [];
  const stockWorth  = d.stock_worth   || 0;
  const cashBalance = d.cash_balance  || 0;
  const partyRec    = d.total_party_receivable || 0;
  const gstTotal    = gstRows.reduce((s,r) => s + (r.amount||0), 0);
  const totalAssets = stockWorth + cashBalance + partyRec + gstTotal;
  const totalPay    = d.total_payable || 0;
  const net         = totalAssets - totalPay;

  const { jsPDF } = window.jspdf;
  const doc  = new jsPDF('p','pt','a4');
  const pW   = doc.internal.pageSize.width;
  const pH   = doc.internal.pageSize.height;
  const today = new Date().toLocaleDateString('en-PK',{day:'2-digit',month:'short',year:'numeric'});

  function drawHeader() {
    doc.setFillColor(5,150,105); doc.rect(0,0,pW,36,'F');
    doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(255,255,255);
    doc.text('Financee', 28, 23);
    doc.setFont('helvetica','normal'); doc.setFontSize(9);
    doc.text('Company Position Report', pW-28, 23, {align:'right'});
    doc.setFillColor(240,253,244); doc.rect(0,36,pW,22,'F');
    doc.setFont('helvetica','italic'); doc.setFontSize(8); doc.setTextColor(100,116,139);
    doc.text(`As of: ${mprFmtDate(d.as_of_date)}`, 28, 51);
    doc.text(`Generated: ${today}`, pW-28, 51, {align:'right'});
    doc.setDrawColor(209,250,229); doc.setLineWidth(0.5); doc.line(0,58,pW,58);
  }

  drawHeader();
  let y = 72;

  function section(title, rows, isTotals) {
    doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(100,116,139);
    doc.text(title.toUpperCase(), 28, y); y += 14;
    rows.forEach(([label, amount]) => {
      doc.setFont('helvetica', isTotals ? 'bold' : 'normal');
      doc.setFontSize(8.5); doc.setTextColor(30,41,59);
      doc.text(label, 36, y);
      doc.text(mprFmt(amount), pW-28, y, {align:'right'});
      y += 13;
    });
    y += 4;
  }

  // Receivables
  section('STOCK', [['Total Stock Worth', stockWorth]]);
  section('PARTY RECEIVABLES', (d.receivables||[]).map(r=>[r.name, r.balance]));
  if (gstRows.length) section('GST / FOREIGN RECEIVABLES', gstRows.map(r=>[r.label, r.amount]));
  section('CASH', [['Cash Balance', cashBalance]]);

  doc.setDrawColor(209,250,229); doc.setLineWidth(1); doc.line(28,y,pW-28,y); y+=8;
  doc.setFont('helvetica','bold'); doc.setFontSize(9.5); doc.setTextColor(5,150,105);
  doc.text('TOTAL RECEIVABLE', 28, y);
  doc.text(mprFmt(totalAssets), pW-28, y, {align:'right'}); y+=20;

  // Payables
  section('PARTY PAYABLES', (d.payables||[]).map(r=>[r.name, r.balance]));
  doc.setDrawColor(252,165,165); doc.setLineWidth(1); doc.line(28,y,pW-28,y); y+=8;
  doc.setFont('helvetica','bold'); doc.setFontSize(9.5); doc.setTextColor(220,38,38);
  doc.text('TOTAL PAYABLE', 28, y);
  doc.text(mprFmt(totalPay), pW-28, y, {align:'right'}); y+=22;

  // Net
  const posColor = net >= 0 ? [5,150,105] : [220,38,38];
  doc.setFillColor(...posColor, 15); doc.roundedRect(28,y,pW-56,32,4,4,'F');
  doc.setFont('helvetica','bold'); doc.setFontSize(11); doc.setTextColor(...posColor);
  doc.text('Net Company Position', 40, y+21);
  doc.text(mprFmt(Math.abs(net)), pW-40, y+21, {align:'right'});

  doc.save(`Company_Position_${d.as_of_date}.pdf`);
}

// ─────────────────────────────────────────────────────────────────────────────
//  PDF — Income Statement
// ─────────────────────────────────────────────────────────────────────────────
function mprPdfIncome() {
  if (!_mprLastData || _mprLastData.report_type !== 'income') {
    Swal.fire('No Data', 'Generate the report first.', 'info'); return;
  }
  const d = _mprLastData;
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF('p','pt','a4');
  const pW  = doc.internal.pageSize.width;
  const today = new Date().toLocaleDateString('en-PK',{day:'2-digit',month:'short',year:'numeric'});

  function drawHeader() {
    doc.setFillColor(5,150,105); doc.rect(0,0,pW,36,'F');
    doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(255,255,255);
    doc.text('Financee', 28, 23);
    doc.setFont('helvetica','normal'); doc.setFontSize(9);
    doc.text('Income Statement', pW-28, 23, {align:'right'});
    doc.setFillColor(240,253,244); doc.rect(0,36,pW,22,'F');
    doc.setFont('helvetica','italic'); doc.setFontSize(8); doc.setTextColor(100,116,139);
    doc.text(`${mprFmtDate(d.from_date)} – ${mprFmtDate(d.to_date)}`, 28, 51);
    doc.text(`Generated: ${today}`, pW-28, 51, {align:'right'});
    doc.setDrawColor(209,250,229); doc.setLineWidth(0.5); doc.line(0,58,pW,58);
  }

  drawHeader();

  const rows = [
    ['Sales Revenue',           mprFmt(d.sales_revenue)],
    ['Less: Cost of Goods Sold', `(${mprFmt(d.cogs)})`],
    ['Gross Profit',            mprFmt(d.gross_profit)],
    ['', ''],
    ...(d.expenses||[]).map(e => [e.category, mprFmt(e.amount)]),
    ['Total Operating Expenses', `(${mprFmt(d.total_expenses)})`],
    ['', ''],
    [d.net_income >= 0 ? 'NET INCOME' : 'NET LOSS', mprFmt(Math.abs(d.net_income))],
  ];

  doc.autoTable({
    startY: 70,
    margin: { left: 28, right: 28 },
    head: [['Description', 'Amount (PKR)']],
    body: rows,
    theme: 'grid',
    headStyles: { fillColor: [5,150,105], textColor:[255,255,255], fontStyle:'bold', fontSize:8.5 },
    bodyStyles: { fontSize: 8.5, textColor:[30,41,59] },
    columnStyles: { 1: { halign:'right', fontStyle:'bold' } },
    didParseCell: (data) => {
      if (data.row.index === rows.length - 1) {
        data.cell.styles.fontStyle = 'bold';
        data.cell.styles.fillColor = d.net_income >= 0 ? [240,253,244] : [255,241,242];
        data.cell.styles.textColor = d.net_income >= 0 ? [5,150,105] : [220,38,38];
      }
      if (data.row.index === 2) {  // Gross Profit row
        data.cell.styles.fontStyle = 'bold';
        data.cell.styles.fillColor = [248,250,252];
      }
    }
  });

  doc.save(`Income_Statement_${d.from_date}_to_${d.to_date}.pdf`);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Print helpers (browser print)
// ─────────────────────────────────────────────────────────────────────────────
function mprPrintPosition() {
  const el = document.getElementById('mpr-position-card');
  if (!el) { Swal.fire('No Data', 'Generate the report first.', 'info'); return; }
  mprPrintElement(el, 'Company Position');
}

function mprPrintIncome() {
  const el = document.getElementById('mpr-income-card');
  if (!el) { Swal.fire('No Data', 'Generate the report first.', 'info'); return; }
  mprPrintElement(el, 'Income Statement');
}

function mprPrintElement(el, title) {
  const win = window.open('', '_blank', 'width=900,height=700');
  win.document.write(`<!DOCTYPE html><html><head>
    <title>${title}</title>
    <style>
      body{font-family:system-ui,sans-serif;padding:24px;color:#1e293b;}
      table{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:12px;}
      td{padding:6px 8px;border-bottom:1px solid #e2e8f0;}
      td:last-child{text-align:right;font-weight:600;}
      .mpr-col-header{font-size:11px;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;padding-bottom:4px;border-bottom:2px solid #059669;
        color:#059669;margin-bottom:6px;}
      .mpr-col-header.mpr-liab{border-color:#dc2626;color:#dc2626;}
      .mpr-position-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:20px;}
      .mpr-net-bar,.mpr-income-banner{background:#f0fdf4;border:2px solid #6ee7b7;
        border-radius:8px;padding:16px 20px;display:flex;justify-content:space-between;
        align-items:center;margin-top:8px;}
      .mpr-net-bar.mpr-negative,.mpr-income-banner.mpr-loss{background:#fff1f2;border-color:#fca5a5;}
      .mpr-net-value,.mpr-income-banner-value{font-size:22px;font-weight:800;color:#059669;}
      .mpr-net-bar.mpr-negative .mpr-net-value,
      .mpr-income-banner.mpr-loss .mpr-income-banner-value{color:#dc2626;}
      .mpr-section-header td{font-size:11px;font-weight:700;text-transform:uppercase;
        color:#64748b;background:#f8fafc;border-bottom:none;padding-top:14px;}
      .mpr-subtotal td{font-weight:700;border-top:2px solid #e2e8f0;border-bottom:none;}
      .mpr-subtotal td:last-child{color:#059669;}
      .mpr-income-section{border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:10px;}
      .mpr-income-section-title{font-size:11px;font-weight:700;text-transform:uppercase;
        padding:6px 10px;background:#f8fafc;color:#64748b;border-bottom:1px solid #e2e8f0;}
      .mpr-total-row td{font-weight:700;background:#f8fafc;}
      .mpr-green{color:#059669!important;} .mpr-red{color:#dc2626!important;}
      h1{font-size:16px;margin:0 0 2px;} .subtitle{font-size:12px;color:#64748b;margin:0 0 20px;}
    </style>
  </head><body>
    <h1>${title}</h1>
    ${el.querySelector('.mpr-report-subtitle') ? `<p class="subtitle">${el.querySelector('.mpr-report-subtitle').textContent}</p>` : ''}
    ${el.innerHTML}
  </body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { win.print(); }, 400);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  mprSelectReport('position');
});