// ==========================
// 🧭 Report Selector
// ==========================
// function selectReport(type) {
//   $(".report-btn").removeClass("active");
//   if (type === "ledger") $("#btn-ledger").addClass("active");
//   else $("#btn-trial").addClass("active");

//   $("#reportHeader").html("");
//   $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);

//   if (type === "ledger") {
//     renderLedgerForm();
//   } else {
//     $("#report-form-container").html("");
//     fetchTrialBalance();
//   }
// }

function selectReport(type) {
  $(".report-btn").removeClass("active");
  
  if (type === "ledger") {
    $("#btn-ledger").addClass("active");
  } else if (type === "cash-ledger") {
    $("#btn-cash-ledger").addClass("active");
  } else {
    $("#btn-trial").addClass("active");
  }

  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);

  if (type === "ledger") {
    renderLedgerForm();
  } else if (type === "cash-ledger") {
    renderCashLedgerForm();
  } else {
    $("#report-form-container").html("");
    fetchTrialBalance();
  }
}

// ==========================
// 💵 Cash Ledger Form
// ==========================
function renderCashLedgerForm() {
  const today = new Date().toISOString().split("T")[0];
  const currentYear = new Date().getFullYear();
  const yearStart = `${currentYear}-01-01`;
  
  const formHTML = `
    <div class="form-row">
      <label for="cash_from_date">From Date:</label>
      <input type="date" id="cash_from_date" value="${yearStart}" required>
      <label for="cash_to_date">To Date:</label>
      <input type="date" id="cash_to_date" value="${today}" required>
      <button class="generate-btn" onclick="fetchCashLedger()">Generate</button>
    </div>
  `;
  $("#report-form-container").html(formHTML);
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Select date range to generate cash ledger</td></tr>`);
}

// ==========================
// 💵 Fetch Cash Ledger
// ==========================
function fetchCashLedger() {
  const fromDate = $("#cash_from_date").val();
  const toDate = $("#cash_to_date").val();

  if (!fromDate || !toDate) {
    Swal.fire("Missing Fields", "Please select both dates.", "warning");
    return;
  }

  Swal.fire({
    title: "Fetching Cash Ledger...",
    text: "Please wait while data loads.",
    didOpen: () => Swal.showLoading(),
    allowOutsideClick: false,
  });

  fetch("/accountsReports/cash-ledger/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
  })
    .then((res) => res.json())
    .then((data) => {
      Swal.close();
      if (data.error) {
        Swal.fire("Error", data.error, "error");
      } else {
        renderTable(data);
      }
    })
    .catch(() => {
      Swal.fire("Error", "Unable to fetch cash ledger data.", "error");
    });
}

// ==========================
// 🧾 Detailed Ledger Form
// ==========================
function renderLedgerForm() {
  const today = new Date().toISOString().split("T")[0];
  const fromDefault = "2000-01-01";
  const formHTML = `
    <div class="form-row autocomplete-container">
        <input type="text" id="search_name" name="search_name"
                placeholder="Enter Party Name"
                autocomplete="off"
                data-autocomplete-url="/parties/autocomplete-party">
        <div id="suggestions"></div>
    </div>
    <div class="form-row">
      <input type="date" id="from_date" value="${fromDefault}" required>
      <input type="date" id="to_date" value="${today}" required>
      <button class="generate-btn" onclick="fetchLedgerReport()">Generate</button>
    </div>
  `;
  $("#report-form-container").html(formHTML);
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Enter filters to generate ledger</td></tr>`);
  initAutocomplete();
}

// ==========================
// 📘 Fetch Detailed Ledger
// ==========================
function fetchLedgerReport() {
  const partyName = $("#search_name").val().trim();
  const fromDate = $("#from_date").val();
  const toDate = $("#to_date").val();

  if (!partyName || !fromDate || !toDate) {
    Swal.fire("Missing Fields", "Please fill all input fields.", "warning");
    return;
  }

  Swal.fire({
    title: "Fetching...",
    text: "Please wait while ledger data loads.",
    didOpen: () => Swal.showLoading(),
    allowOutsideClick: false,
  });

  fetch("/accountsReports/detailed-ledger/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({ party_name: partyName, from_date: fromDate, to_date: toDate }),
  })
    .then((res) => res.json())
    .then((data) => {
      Swal.close();
      if (data.error) {
        Swal.fire("Error", data.error, "error");
      } else {
        renderTable(data);
      }
    })
    .catch(() => {
      Swal.fire("Error", "Unable to fetch ledger data.", "error");
    });
}

// ==========================
// 📊 Fetch Trial Balance
// ==========================
function fetchTrialBalance() {
  Swal.fire({
    title: "Loading Trial Balance...",
    didOpen: () => Swal.showLoading(),
    allowOutsideClick: false,
  });

  fetch("/accountsReports/trial-balance/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
  })
    .then((res) => res.json())
    .then((data) => {
      Swal.close();
      if (data.error) {
        Swal.fire("Error", data.error, "error");
      } else {
        renderTable(data);
      }
    })
    .catch(() => {
      Swal.fire("Error", "Unable to fetch trial balance.", "error");
    });
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

// // ==========================
// // 🧾 Download Table as PDF
// // ==========================
// $(document).on("click", "#download_pdf", function () {
//   const { jsPDF } = window.jspdf;
//   const doc = new jsPDF("p", "pt", "a4");

//   const activeReport = $(".report-btn.active").attr("id") === "btn-ledger" ? "Detailed Ledger" : "Trial Balance";
//   const party = $("#search_name").val() || "All";
//   const fromDate = $("#from_date").val() || "N/A";
//   const toDate = $("#to_date").val() || "N/A";

//   doc.setFontSize(14);
//   doc.text(`${activeReport} Report`, 40, 40);
//   doc.setFontSize(10);
//   if (activeReport === "Detailed Ledger") {
//     doc.text(`Party: ${party}`, 40, 60);
//     doc.text(`From: ${fromDate}    To: ${toDate}`, 40, 75);
//   }

//   doc.autoTable({
//     html: "#reportTable",
//     startY: activeReport === "Detailed Ledger" ? 100 : 60,
//     theme: "grid",
//     headStyles: { fillColor: [25, 135, 84] },
//     styles: { fontSize: 9 },
//   });

//   const totalPages = doc.internal.getNumberOfPages();
//   for (let i = 1; i <= totalPages; i++) {
//     doc.setPage(i);
//     doc.setFontSize(8);
//     doc.text(`Page ${i} of ${totalPages}`, doc.internal.pageSize.width - 60, doc.internal.pageSize.height - 20);
//   }

//   const filename = `${activeReport.replace(" ", "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
//   doc.save(filename);
// });
// ==========================
// 🧾 Download Table as PDF
// ==========================
$(document).on("click", "#download_pdf", function () {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "pt", "a4");

  const activeBtn = $(".report-btn.active");
  let activeReport = "Report";
  let party = "";
  let fromDate = "";
  let toDate = "";

  // Determine which report is active
  if (activeBtn.attr("id") === "btn-ledger") {
    activeReport = "Detailed Ledger";
    party = $("#search_name").val() || "All";
    fromDate = $("#from_date").val() || "N/A";
    toDate = $("#to_date").val() || "N/A";
  } else if (activeBtn.attr("id") === "btn-cash-ledger") {
    activeReport = "Cash Ledger";
    fromDate = $("#cash_from_date").val() || "N/A";
    toDate = $("#cash_to_date").val() || "N/A";
  } else if (activeBtn.attr("id") === "btn-trial") {
    activeReport = "Trial Balance";
  }

  // Add report title
  doc.setFontSize(14);
  doc.text(`${activeReport} Report`, 40, 40);
  doc.setFontSize(10);
  
  // Add metadata based on report type
  let startY = 60;
  if (activeReport === "Detailed Ledger") {
    doc.text(`Party: ${party}`, 40, 60);
    doc.text(`From: ${fromDate}    To: ${toDate}`, 40, 75);
    startY = 100;
  } else if (activeReport === "Cash Ledger") {
    doc.text(`From: ${fromDate}    To: ${toDate}`, 40, 60);
    startY = 85;
  }

  // Generate table
  doc.autoTable({
    html: "#reportTable",
    startY: startY,
    theme: "grid",
    headStyles: { fillColor: [25, 135, 84] },
    styles: { fontSize: 9 },
  });

  // Add page numbers
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.text(`Page ${i} of ${totalPages}`, doc.internal.pageSize.width - 60, doc.internal.pageSize.height - 20);
  }

  // Save with appropriate filename
  const filename = `${activeReport.replace(/ /g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
  doc.save(filename);
});


// ==========================
// 🔐 Utility: CSRF Token
// ==========================
function getCSRFToken() {
  const name = "csrftoken=";
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookies = decodedCookie.split(";");
  for (let c of cookies) {
    c = c.trim();
    if (c.indexOf(name) === 0) return c.substring(name.length, c.length);
  }
  return "";
}

// ==========================
// ✨ Autocomplete with Keyboard Nav
// ==========================
function initAutocomplete() {


  const $input = $("#search_name");
  const $suggestions = $("#suggestions");
  const autocompleteUrl = $input.data("autocomplete-url");

  let selectedIndex = -1;
  let currentSuggestions = [];

  $input.on("input", function () {
    const query = $(this).val();
    selectedIndex = -1;
    if (query.length < 1) {
      $suggestions.hide();
      return;
    }

    $.ajax({
      url: autocompleteUrl,
      data: { term: query },
      dataType: "json",
      success: function (data) {
        $suggestions.empty();
        currentSuggestions = data;

        if (data.length > 0) {
          data.forEach((party, index) => {
            $("<div>")
              .addClass("suggestion-item")
              .text(party)
              .css({ padding: "5px", cursor: "pointer", borderBottom: "1px solid #ddd" })
              .on("mouseenter", function () {
                $(".suggestion-item").removeClass("highlight");
                $(this).addClass("highlight");
                selectedIndex = index;
              })
              .on("click", function () {
                $input.val(party);
                $suggestions.hide();
              })
              .appendTo($suggestions);
          });
          $suggestions.show();
        } else {
          $suggestions.hide();
        }
      },
      error: function (xhr, status, error) {
        console.error("AJAX error:", status, error);
      },
    });
  });

  $input.on("keydown", function (e) {
    const items = $suggestions.children(".suggestion-item");

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (items.length > 0) {
        selectedIndex = (selectedIndex + 1) % items.length;
        items.removeClass("highlight");
        $(items[selectedIndex]).addClass("highlight");
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (items.length > 0) {
        selectedIndex = (selectedIndex - 1 + items.length) % items.length;
        items.removeClass("highlight");
        $(items[selectedIndex]).addClass("highlight");
      }
    } else if (e.key === "Enter") {
      if (currentSuggestions.length === 1) {
        e.preventDefault();
        $input.val(currentSuggestions[0]);
        $suggestions.hide();
      } else if (selectedIndex >= 0 && selectedIndex < items.length) {
        e.preventDefault();
        const selectedText = $(items[selectedIndex]).text();
        $input.val(selectedText);
        $suggestions.hide();
      }
    } else if (e.key === "Escape") {
      $suggestions.hide();
    }
  });

  $(document).on("click", function (e) {
    if (!$(e.target).closest("#search_name, #suggestions").length) {
      $suggestions.hide();
    }
  });
}

// ==========================
// 🚀 Init Default View
// ==========================
$(document).ready(() => {
  selectReport("ledger");
});
