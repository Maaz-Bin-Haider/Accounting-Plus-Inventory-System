function fetchDetailedLedger(event) {
  event.preventDefault();

  const partyName = document.getElementById("party_name").value.trim();
  const fromDate = document.getElementById("from_date").value;
  const toDate = document.getElementById("to_date").value;

  if (!partyName || !fromDate || !toDate) {
    Swal.fire({
      title: "Missing Data",
      text: "Please fill all required fields.",
      icon: "warning",
      confirmButtonColor: "#1d3557",
    });
    return;
  }

  Swal.fire({
    title: "Loading...",
    text: "Fetching ledger data, please wait.",
    allowOutsideClick: false,
    didOpen: () => {
      Swal.showLoading();
    }
  });

  fetch("/accountsReports/detailed-ledger/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({
      party_name: partyName,
      from_date: fromDate,
      to_date: toDate
    })
  })
  .then(response => response.json())
  .then(data => {
    Swal.close();
    renderLedgerTable(data);
  })
  .catch(() => {
    Swal.fire({
      title: "Error",
      text: "Failed to fetch ledger data.",
      icon: "error",
      confirmButtonColor: "#1d3557",
    });
  });
}

function renderLedgerTable(data) {
  const header = document.getElementById("ledgerHeader");
  const body = document.getElementById("ledgerBody");

  if (!data || data.length === 0) {
    body.innerHTML = `<tr><td colspan="10" class="no-data">No records found for selected filters.</td></tr>`;
    header.innerHTML = "";
    return;
  }

  // Create table headers
  const columns = Object.keys(data[0]);
  header.innerHTML = columns.map(col => `<th>${col.replace(/_/g, ' ')}</th>`).join("");

  // Populate table rows
  body.innerHTML = data.map(row => `
    <tr>
      ${columns.map(col => `<td>${row[col] ?? ""}</td>`).join("")}
    </tr>
  `).join("");
}

function resetLedgerForm() {
  document.getElementById("ledgerForm").reset();
  document.getElementById("ledgerHeader").innerHTML = "";
  document.getElementById("ledgerBody").innerHTML = `
    <tr><td colspan="6" class="no-data">Please run a search to view data</td></tr>`;
}

// Utility to get CSRF Token from cookie
function getCSRFToken() {
  const name = "csrftoken=";
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookies = decodedCookie.split(";");
  for (let c of cookies) {
    while (c.charAt(0) === " ") c = c.substring(1);
    if (c.indexOf(name) === 0) return c.substring(name.length, c.length);
  }
  return "";
}
