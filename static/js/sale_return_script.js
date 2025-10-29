// ------------------------------
//  Sale Return Script
// ------------------------------

// CSRF
function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(";").map(c => c.trim());
  for (let c of cookies) {
    if (c.startsWith(name + "=")) return decodeURIComponent(c.split("=")[1]);
  }
  return null;
}

// 🧩 Add Serial Row
function addSerial(autoFocus = true) {
  const serialsDiv = document.getElementById("serials");
  const row = document.createElement("div");
  row.className = "serial-row";

  const serialInput = document.createElement("input");
  serialInput.type = "text";
  serialInput.placeholder = "Enter Serial Number";
  serialInput.className = "serial-input";
  serialInput.oninput = updateCount;
  serialInput.onkeydown = handleEnterKey;

  const itemInput = document.createElement("input");
  itemInput.type = "text";
  itemInput.placeholder = "Item Name";
  itemInput.className = "item-input";
  itemInput.readOnly = true;

  const itemPrice = document.createElement("input");
  itemPrice.type = "text";
  itemPrice.placeholder = "Item Price";
  itemPrice.className = "item-input";
  itemPrice.readOnly = true;

  const removeBtn = document.createElement("button");
  removeBtn.innerHTML = "×";
  removeBtn.className = "remove-btn";
  removeBtn.title = "Remove this serial";
  removeBtn.onclick = () => { row.remove(); updateCount(); };

  serialInput.addEventListener("change", function() {
    const serialValue = serialInput.value.trim();
    if (serialValue) {
      fetch(`/saleReturn/lookup/${encodeURIComponent(serialValue)}/`)
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            itemInput.value = data.item_name;
            itemPrice.value = data.item_price;
          } else {
            itemInput.value = "";
            Swal.fire({ icon: "error", title: "Not Found", text: data.message || "Serial not found." });
          }
        })
        .catch(() => Swal.fire({ icon: "error", title: "Error", text: "Failed to fetch serial details." }));
    } else itemInput.value = "";
  });

  row.appendChild(serialInput);
  row.appendChild(itemInput);
  row.appendChild(itemPrice);
  row.appendChild(removeBtn);
  serialsDiv.appendChild(row);

  if (autoFocus) serialInput.focus();
  updateCount();
}

// 🧮 Count serials
function updateCount() {
  const serials = Array.from(document.querySelectorAll(".serial-input"))
    .map(i => i.value.trim())
    .filter(v => v !== "");
  document.getElementById("totalQty").textContent = serials.length;
}

// Handle Enter
function handleEnterKey(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    if (e.target.value.trim()) e.target.dispatchEvent(new Event("change"));
    const inputs = Array.from(document.querySelectorAll(".serial-input"));
    const index = inputs.indexOf(e.target);
    if (index + 1 < inputs.length) inputs[index + 1].focus();
  }
}

// Submit Sale Return
function submitSaleReturn(event) {
  event.preventDefault();
  const form = event.target;
  const action = form.querySelector('button[type="submit"][clicked="true"]')?.value;

  const customer = document.getElementById("search_name").value.trim();
  if (!customer) {
    Swal.fire({ icon: "warning", title: "Missing Customer", text: "Enter a customer name first." });
    return;
  }

  let returnDate = document.getElementById("return_date").value || new Date().toISOString().slice(0, 10);
  const serials = Array.from(document.querySelectorAll(".serial-input")).map(i => i.value.trim()).filter(Boolean);

  if (serials.length === 0) {
    Swal.fire({ icon: "warning", title: "No Serials", text: "Enter at least one serial number." });
    return;
  }

  const payload = {
    return_id: document.getElementById("current_return_id").value || "",
    party_name: customer,
    return_date: returnDate,
    serials,
    action
  };

  fetch("/saleReturn/create-sale-return/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    if (data.success)
      Swal.fire({ icon: "success", title: "✅ Success", text: data.message, timer: 1500, showConfirmButton: false })
        .then(() => window.location.reload());
    else Swal.fire({ icon: "error", title: "Error", text: data.message });
  })
  .catch(err => Swal.fire({ icon: "error", title: "Network Error", text: err.message }));
}

// Autocomplete for Customer
$(document).ready(function() {
  const autocompleteUrl = $("#search_name").data("autocomplete-url");
  let selectedIndex = -1;

  $("#search_name").on("input", function() {
    const query = $(this).val();
    const suggestionsBox = $("#suggestions");
    selectedIndex = -1;

    if (query.length >= 1) {
      $.ajax({
        url: autocompleteUrl,
        data: { term: query },
        dataType: "json",
        success: function(data) {
          suggestionsBox.empty();
          if (data.length > 0) {
            data.forEach(customer => {
              $("<div>").addClass("suggestion-item").text(customer)
                .css({ padding: "5px", cursor: "pointer", borderBottom: "1px solid #ddd" })
                .appendTo(suggestionsBox)
                .on("click", function() {
                  $("#search_name").val(customer);
                  suggestionsBox.hide();
                  $("#return_date").focus();
                });
            });
            suggestionsBox.show();
          } else suggestionsBox.hide();
        }
      });
    } else suggestionsBox.hide();
  });

  $("#search_name").on("keydown", function (e) {
    let items = $("#suggestions .suggestion-item");

      if (items.length === 0) return;

      // 👉 Auto-select if only one suggestion and Enter is pressed
      if (e.key === "Enter" && items.length === 1) {
          e.preventDefault();
          items.eq(0).trigger("click");
          return;
      }

      if (e.key === "ArrowDown") {
          e.preventDefault();
          selectedIndex = (selectedIndex + 1) % items.length;
          items.removeClass("highlight");
          let selectedItem = items.eq(selectedIndex).addClass("highlight")[0];
          selectedItem.scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
          e.preventDefault();
          selectedIndex = (selectedIndex - 1 + items.length) % items.length;
          items.removeClass("highlight");
          let selectedItem = items.eq(selectedIndex).addClass("highlight")[0];
          selectedItem.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
          e.preventDefault();
          if (selectedIndex >= 0) {
              items.eq(selectedIndex).trigger("click");
          }
      }
  });

  $(document).on("click", e => {
    if (!$(e.target).closest("#search_name, #suggestions").length) $("#suggestions").hide();
  });

  for (let i = 0; i < 3; i++) addSerial(false);
  document.getElementById("return_date").value = new Date().toISOString().slice(0, 10);
});

// Track clicked submit button
document.querySelectorAll('button[type="submit"]').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('button[type="submit"]').forEach(b => b.removeAttribute('clicked'));
    this.setAttribute('clicked', 'true');
  });
});

// Navigation
async function navigateSaleReturn(action) {
  try {
    const currentId = document.getElementById("current_return_id").value || "";
    const res = await fetch(`/saleReturn/get-sale-return/?action=${action}&current_id=${currentId}`, {
      method: "GET", headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    let data = await res.json();
    if (!data || data.success === false)
      return Swal.fire({ icon: "error", title: "Error", text: data.message || "No sale-return found!" });

    if (typeof data === "string") data = JSON.parse(data);
    renderSaleReturnData(data);
  } catch (e) {
    Swal.fire({ icon: "error", title: "Error", text: e.message });
  }
}

function renderSaleReturnData(data) {
  document.getElementById("search_name").value = data.Customer || "";
  document.getElementById("return_date").value = data.return_date || "";
  document.getElementById("current_return_id").value = data.sales_return_id || "";
  const serialsDiv = document.getElementById("serials");
  serialsDiv.innerHTML = "";

  if (Array.isArray(data.items)) {
    data.items.forEach(item => {
      const row = document.createElement("div");
      row.className = "serial-row";

      const serialInput = document.createElement("input");
      serialInput.type = "text";
      serialInput.value = item.serial_number || "";
      serialInput.className = "serial-input";

      const itemInput = document.createElement("input");
      itemInput.type = "text";
      itemInput.value = item.item_name || "";
      itemInput.className = "item-input";
      itemInput.readOnly = true;

      const itemPrice = document.createElement("input");
      itemPrice.type = "text";
      itemPrice.value = item.sold_price || "";
      itemPrice.className = "item-input";
      itemPrice.readOnly = true;

      const removeBtn = document.createElement("button");
      removeBtn.innerHTML = "×";
      removeBtn.className = "remove-btn";
      removeBtn.onclick = () => { row.remove(); updateCount(); };

      row.appendChild(serialInput);
      row.appendChild(itemInput);
      row.appendChild(itemPrice);
      row.appendChild(removeBtn);
      serialsDiv.appendChild(row);
    });
  }

  const submitBtn = document.querySelector("#saleReturnForm button[type=submit]");
  submitBtn.textContent = data.sale_return_id ? "Update Sale Return" : "Save Sale Return";
  updateCount();
}

// Delete confirmation
const deleteButton = document.querySelector(".delete-btn");
function confirmDelete(e) {
  e.preventDefault();
  Swal.fire({
    title: "Are you sure?",
    text: "This sale return will be permanently deleted!",
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#d33",
    cancelButtonColor: "#3085d6",
    confirmButtonText: "Yes, delete it!"
  }).then(result => {
    if (result.isConfirmed) {
      deleteButton.removeEventListener("click", confirmDelete);
      deleteButton.click();
      setTimeout(() => deleteButton.addEventListener("click", confirmDelete), 100);
    }
  });
}
deleteButton.addEventListener("click", confirmDelete);


async function fetchSaleReturnSummary(from = null, to = null) {
  try {
    let url = "/saleReturn/get-sale-return-summary/";
    if (from && to) {
      url += `?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
    }

    const response = await fetch(url);
    const data = await response.json();

    if (!data.success && !Array.isArray(data)) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: data.message || "Failed to fetch sale-return summary.",
      });
      return;
    }

    // ✅ Build the table rows
    let rows = "";
    if (Array.isArray(data) && data.length > 0) {
      data.forEach((saleReturn, idx) => {
        rows += `
          <tr 
            class="return-row"
            data-vendor="${saleReturn.customer.toLowerCase()}"
            style="cursor:pointer; transition:background 0.2s;"
            onclick="viewSaleReturnDetails(${saleReturn.sales_return_id})"
            onmouseover="this.style.background='#f3f4f6';"
            onmouseout="this.style.background='';"
          >
            <td>${idx + 1}</td>
            <td>${saleReturn.sales_return_id}</td>
            <td>${saleReturn.return_date}</td>
            <td>${saleReturn.customer}</td>
            <td style="text-align:right;">${saleReturn.total_amount.toFixed(2)}</td>
          </tr>`;
      });
    } else {
      rows = `<tr><td colspan="5" style="text-align:center;">No data found</td></tr>`;
    }

    // 🧾 Build styled HTML with search bar
    const htmlContent = `
      <style>
        .return-container {
          font-family: 'Inter', system-ui, sans-serif;
          max-height: 450px;
          overflow-y: auto;
          padding: 5px;
          border-radius: 8px;
        }
        .return-search {
          width: 100%;
          padding: 8px 12px;
          margin-bottom: 10px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          outline: none;
          transition: all 0.2s;
        }
        .return-search:focus {
          border-color: #2563eb;
          box-shadow: 0 0 0 2px rgba(37,99,235,0.1);
        }
        table.return-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }
        table.return-table th, table.return-table td {
          padding: 8px 10px;
          border-bottom: 1px solid #e5e7eb;
        }
        table.return-table th {
          background: #f9fafb;
          font-weight: 600;
          color: #374151;
        }
        table.return-table tbody tr:hover {
          background: #f3f4f6;
        }
      </style>

      <input 
        type="text" 
        class="return-search" 
        placeholder="🔍 Search by Customer name..." 
        onkeyup="filterSaleReturnTable(this.value)" 
      />

      <div class="return-container">
        <table class="return-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Return ID</th>
              <th>Date</th>
              <th>Vendor</th>
              <th style="text-align:right;">Total Amount</th>
            </tr>
          </thead>
          <tbody id="purchaseReturnSummaryBody">
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  
    // 🎉 SweetAlert popup
    Swal.fire({
      title: "📜 Sale Return Summary",
      html: htmlContent,
      width: "750px",
      confirmButtonText: "Close",
      showConfirmButton: true,
      focusConfirm: false,
      allowOutsideClick: false,
      allowEnterKey: true,
      allowEscapeKey: true,
      didOpen: (popup) => {
        const input = popup.querySelector(".return-search");

        document.querySelectorAll("input, textarea, select").forEach(el => el.blur());
        popup.addEventListener("focusin", e => e.stopPropagation());

        // Force focus into search field
        setTimeout(() => {
          if (input) {
            input.focus();
            input.select();
            setTimeout(() => input.focus(), 400);
            setTimeout(() => input.focus(), 800);
          }
        }, 100);
      }
    });

  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Network Error",
      text: error.message || "Unable to fetch sale-return summary. Please try again!",
    });
  }
}




function filterSaleReturnTable(q) {
  q = q.toLowerCase().trim();
  document.querySelectorAll("#saleReturnSummaryBody tr").forEach(r =>
    r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none"
  );
}
viewSaleReturnDetails

function saleReturnHistory() { fetchSaleReturnSummary(); }



// 📅 2️⃣ Button: Fetch Purchase Returns by Date Range
function saleReturnDateWise() {
  const today = new Date().toISOString().split("T")[0];
  Swal.fire({
    title: "📅 Select Date Range",
    html: `
      <label>From Date</label><br>
      <input type="date" id="fromDate" class="swal2-input" style="width:70%">
      <br>
      <label>To Date</label><br>
      <input type="date" id="toDate" class="swal2-input" style="width:70%" value="${today}">
    `,
    focusConfirm: false,
    showCancelButton: true,
    confirmButtonText: "Fetch Sale Returns",
    preConfirm: () => {
      const fromDate = document.getElementById("fromDate").value;
      const toDate = document.getElementById("toDate").value;
      if (!fromDate || !toDate) {
        Swal.showValidationMessage("⚠️ Both dates are required");
        return false;
      }
      return { fromDate, toDate };
    }
  }).then(result => {
    if (result.isConfirmed) {
      const { fromDate, toDate } = result.value;
      fetchSaleReturnSummary(fromDate, toDate);
    }
  });
}

function viewSaleReturnDetails(id) {
  document.getElementById("current_return_id").value = id;
  navigateSaleReturn("current");
  Swal.close();
}
