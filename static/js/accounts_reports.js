// function fetchDetailedLedger(event) {
//   event.preventDefault();

//   const partyName = document.getElementById("party_name").value.trim();
//   const fromDate = document.getElementById("from_date").value;
//   const toDate = document.getElementById("to_date").value;

//   if (!partyName || !fromDate || !toDate) {
//     Swal.fire({
//       title: "Missing Data",
//       text: "Please fill all required fields.",
//       icon: "warning",
//       confirmButtonColor: "#1d3557",
//     });
//     return;
//   }

//   Swal.fire({
//     title: "Loading...",
//     text: "Fetching ledger data, please wait.",
//     allowOutsideClick: false,
//     didOpen: () => {
//       Swal.showLoading();
//     }
//   });

//   fetch("/accountsReports/detailed-ledger/", {
//     method: "POST",
//     headers: {
//       "Content-Type": "application/json",
//       "X-CSRFToken": getCSRFToken(),
//     },
//     body: JSON.stringify({
//       party_name: partyName,
//       from_date: fromDate,
//       to_date: toDate
//     })
//   })
//   .then(response => response.json())
//   .then(data => {
//     Swal.close();
//     renderLedgerTable(data);
//   })
//   .catch(() => {
//     Swal.fire({
//       title: "Error",
//       text: "Failed to fetch ledger data.",
//       icon: "error",
//       confirmButtonColor: "#1d3557",
//     });
//   });
// }

// function renderLedgerTable(data) {
//   const header = document.getElementById("ledgerHeader");
//   const body = document.getElementById("ledgerBody");

//   if (!data || data.length === 0) {
//     body.innerHTML = `<tr><td colspan="10" class="no-data">No records found for selected filters.</td></tr>`;
//     header.innerHTML = "";
//     return;
//   }

//   // Create table headers
//   const columns = Object.keys(data[0]);
//   header.innerHTML = columns.map(col => `<th>${col.replace(/_/g, ' ')}</th>`).join("");

//   // Populate table rows
//   body.innerHTML = data.map(row => `
//     <tr>
//       ${columns.map(col => `<td>${row[col] ?? ""}</td>`).join("")}
//     </tr>
//   `).join("");
// }

// function resetLedgerForm() {
//   document.getElementById("ledgerForm").reset();
//   document.getElementById("ledgerHeader").innerHTML = "";
//   document.getElementById("ledgerBody").innerHTML = `
//     <tr><td colspan="6" class="no-data">Please run a search to view data</td></tr>`;
// }

// // Utility to get CSRF Token from cookie
// function getCSRFToken() {
//   const name = "csrftoken=";
//   const decodedCookie = decodeURIComponent(document.cookie);
//   const cookies = decodedCookie.split(";");
//   for (let c of cookies) {
//     while (c.charAt(0) === " ") c = c.substring(1);
//     if (c.indexOf(name) === 0) return c.substring(name.length, c.length);
//   }
//   return "";
// }


// ==========================
// 🧭 Report Selector
// ==========================
function selectReport(type) {
  $(".report-btn").removeClass("active");
  if (type === "ledger") $("#btn-ledger").addClass("active");
  else $("#btn-trial").addClass("active");

  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);

  if (type === "ledger") {
    renderLedgerForm();
  } else {
    $("#report-form-container").html("");
    fetchTrialBalance();
  }
}

// ==========================
// 🧾 Detailed Ledger Form
// ==========================
function renderLedgerForm() {
  const formHTML = `
    <div class="form-row">
      <input type="text" id="party_name" placeholder="Enter Party Name" required>
    </div>
    <div class="form-row">
      <input type="date" id="from_date" required>
      <input type="date" id="to_date" required>
      <button class="generate-btn" onclick="fetchLedgerReport()">Generate</button>
    </div>
  `;
  $("#report-form-container").html(formHTML);
  $("#reportHeader").html("");
  $("#reportBody").html(`<tr><td class="no-data">Enter filters to generate ledger</td></tr>`);
}

// ==========================
// 📘 Fetch Detailed Ledger
// ==========================
function fetchLedgerReport() {
  const partyName = $("#party_name").val().trim();
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

// Initialize default view
$(document).ready(() => {
  selectReport("ledger");
});
