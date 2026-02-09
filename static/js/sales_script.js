

function updateQty(row) {
  const serialInputs = row.querySelectorAll(".serials input");
  const qtyBox = row.querySelector(".qty-box");
  let count = 0;
  serialInputs.forEach(input => {
    if (input.value.trim() !== "") count++;
  });
  qtyBox.value = count;
  calculateTotal();
}

function addSerial(row, autoFocus = true) {
  const serialsDiv = row.querySelector(".serials");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Serial";
  input.oninput = () => updateQty(row);
  input.onkeydown = (e) => handleEnterKey(e, input);
  serialsDiv.appendChild(input);
  updateQty(row);

  if (autoFocus) {
    input.focus();
  }
  
}

function removeSerial(row) {
  const serialsDiv = row.querySelector(".serials");
  if (serialsDiv.lastChild) {
    serialsDiv.removeChild(serialsDiv.lastChild);
    updateQty(row);

    // 👇 Focus handling
    const remaining = serialsDiv.querySelectorAll("input");
    if (remaining.length > 0) {
      remaining[remaining.length - 1].focus(); // focus last serial
    } else {
      row.querySelector(".add-serial").focus(); // fallback
    }
  }
}
// <input type="text" class="item_name" placeholder="Item name"></input>

function addItemRow(shouldFocus = true) {
  const itemsDiv = document.getElementById("items");

  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    
    <div class="item_name_field autocomplete-container">
        <input type="text" class="item_name item_search_name" placeholder="Item name"
              autocomplete="off"
              data-autocomplete-url="${autocompleteItemUrl}">
        <div class="items_suggestions"></div>
    </div>
    <input type="number" class="unit_price" step="0.01" placeholder="Unit price">
    <input type="number" class="qty-box" readonly value="0">
    <div class="serials"></div>
    <button type="button" class="custom-btn add-serial">+ Serial</button>
    <button type="button" class="custom-btn remove-serial">- Serial</button>
    <button type="button" class="custom-btn remove-item">Remove</button>
  `;

  row.querySelector(".add-serial").onclick = () => addSerial(row);
  row.querySelector(".remove-serial").onclick = () => removeSerial(row);
  row.querySelector(".remove-item").onclick = () => { row.remove(); calculateTotal(); };
  row.querySelector(".unit_price").oninput = () => calculateTotal();

  itemsDiv.appendChild(row);
  enforceSequentialValidation();

  addSerial(row,false);

  // Only focus item_name if shouldFocus is true
  if (shouldFocus) {
    row.querySelector(".item_name").focus();
  }
}

function calculateTotal() {
  let total = 0;
  const rows = document.querySelectorAll(".item-row");
  rows.forEach(row => {
    const unit_price = parseFloat(row.querySelector(".unit_price").value) || 0;
    const qty = parseInt(row.querySelector(".qty-box").value) || 0;
    total += unit_price * qty;
  });
  document.getElementById("totalAmount").textContent = total.toFixed(2);
}

function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(";").map(c => c.trim());
  for (let c of cookies) {
    if (c.startsWith(name + "=")) {
      return decodeURIComponent(c.split("=")[1]);
    }
  }
  return null;
}

function buildAndSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const action = form.querySelector('button[type="submit"][clicked="true"]')?.value; // ⭐ NEW


  const partyName = document.getElementById("search_name").value.trim();
  let purchaseDate = document.getElementById("sale_date").value;
  if (!purchaseDate) {
    purchaseDate = new Date().toISOString().slice(0,10);
  }
  if (!partyName) {
    Swal.fire({
      icon: "warning",
      title: "Missing Party Name",
      text: "Please enter the party name before submitting.",
      confirmButtonText: "OK"
    });
    document.getElementById("search_name").focus();
    return;
  }
  const items = [];
  const rows = document.querySelectorAll(".item-row");
  rows.forEach(row => {
    const item_name = row.querySelector(".item_name").value.trim();
    const unit_price = parseFloat(row.querySelector(".unit_price").value);
    const serials = Array.from(row.querySelectorAll(".serials input"))
      .map(s => s.value.trim())
      .filter(s => s);
    const qty = serials.length;

    if (item_name && qty > 0 && !isNaN(unit_price) && unit_price > 0) {
      items.push({ item_name, qty, unit_price, serials });
    }
  });
  if (items.length === 0) {
    Swal.fire({
      icon: "warning",
      title: "Invalid Items",
      text: "Please enter at least one valid item with name, unit price, and serial(s).",
      confirmButtonText: "OK"
    });
    return;
  }
  const currentId = document.getElementById("current_sale_id").value || null;
  const payload = {
    sale_id: currentId,
    party_name: partyName,
    sale_date: purchaseDate, 
    items: items,
    action: action,
  };
  // Send JSON to backend
  fetch("/sale/sales/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken()
    },
    body: JSON.stringify(payload)
  })
  .then(async res => {
    if (!res.ok) {
      // Try to extract JSON error if backend sends one
      let errMsg = "Something went wrong on the server.";
      try {
        const errorData = await res.json();
        if (errorData.message) errMsg = errorData.message;
      } catch {
        // fallback to generic error
      }
      throw new Error(errMsg);
    }
    return res.json();
  })
  .then(data => {
    if (data.confirm) {
      // 🔸 Show confirmation SweetAlert
      Swal.fire({
        icon: "warning",
        title: "Confirm Sale",
        text: data.message || "The selling price is lower than the buying price. Do you want to continue?",
        showCancelButton: true,
        confirmButtonText: "Yes, continue",
        cancelButtonText: "No, cancel"
      }).then((result) => {
        if (result.isConfirmed) {
          // Re-submit with confirmation flag
          payload.force = true; // ⚡ tell backend to skip this check
          fetch("/sale/sales/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify(payload)
          })
          .then(res => res.json())
          .then(finalData => {
            if (finalData.success) {
              Swal.fire({
                icon: "success",
                title: "Success 🎉",
                text: finalData.message || "Your sale was submitted successfully!",
                timer: 1500,
                showConfirmButton: false
              }).then(() => window.location.reload());
            } else {
              Swal.fire({
                icon: "error",
                title: "Error",
                text: finalData.message || "There was a problem with your submission."
              });
            }
          });
        }
      });
    } else if (data.success) {
      Swal.fire({
        icon: "success",
        title: "Success 🎉",
        text: data.message || "Your sale was submitted successfully!",
        timer: 1500,
        showConfirmButton: false
      }).then(() => window.location.reload());
    } else {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: data.message || "There was a problem with your submission."
      });
    }
  })
  .catch(err => {
    Swal.fire({
      icon: "error",
      title: "Submission Failed",
      text: err.message || "An unexpected error occurred. Please try again."
    });
  });

}
document.querySelectorAll('button[type="submit"]').forEach(btn => {
  btn.addEventListener('click', function() {
    // Remove 'clicked' from all buttons
    document.querySelectorAll('button[type="submit"]').forEach(b => b.removeAttribute('clicked'));
    // Mark the one that was clicked
    this.setAttribute('clicked', 'true');
  });
});

window.onload = function() {
  for (let i = 0; i < 3; i++) addItemRow(false);
  enforceSequentialValidation();
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("sale_date").value = today;

};

function handleEnterKey(e, input) {
  if (e.key === "Enter") {
    e.preventDefault();
    if (!input.value.trim()) {
      input.focus();
      return;
    }
    const formInputs = Array.from(document.querySelectorAll("input, select, textarea")).filter(el => !el.hasAttribute("readonly"));
    const index = formInputs.indexOf(input);
    if (index > -1 && index < formInputs.length - 1) {
      formInputs[index + 1].focus();
    }
  }
}

function enforceSequentialValidation() {
  const inputs = document.querySelectorAll("input, select, textarea");
  inputs.forEach(input => {
    input.onkeydown = (e) => handleEnterKey(e, input);
    input.onblur = () => { if (!input.value.trim()) input.focus(); };
  });
}

// --------------------------------Auto suggest Party Name-----------------------

$(document).ready(function () {
    let autocompleteUrl = $("#search_name").data("autocomplete-url");
    let selectedIndex = -1; // for keyboard navigation

    $("#search_name").on("input", function () {
        let query = $(this).val();
        let suggestionsBox = $("#suggestions");
        selectedIndex = -1; // reset when typing

        if (query.length >= 1) {
            $.ajax({
                url: autocompleteUrl,
                data: { term: query },
                dataType: "json",
                success: function (data) {
                    suggestionsBox.empty();
                    if (data.length > 0) {
                        data.forEach(function (party) {
                            $("<div>")
                                .addClass("suggestion-item")
                                .text(party)
                                .css({
                                    padding: "5px",
                                    cursor: "pointer",
                                    borderBottom: "1px solid #ddd",
                                })
                                .appendTo(suggestionsBox)
                                .on("click", function () {
                                    $("#search_name").val(party);
                                    suggestionsBox.hide();
                                    $("#sale_date").focus(); // move to next field
                                });
                        });
                        suggestionsBox.show();
                    } else {
                        suggestionsBox.hide();
                    }
                },
            });
        } else {
            suggestionsBox.hide();
        }
    });

    // Keyboard navigation with auto-scroll
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

    $(document).on("click", function (e) {
        if (!$(e.target).closest("#search_name, #suggestions").length) {
            $("#suggestions").hide();
        }
    });
});

// --------------------------------Auto suggest Item Name-----------------------
// suggestionsBox for item names
let selectedIndex = -1; // track highlighted suggestion per input

// Autocomplete input event
$(document).on("input", ".item_search_name", function () {
    let input = $(this);
    let query = input.val();
    let suggestionsBox = input.siblings(".items_suggestions");
    let autocompleteUrl = input.data("autocomplete-url");
    selectedIndex = -1; // reset index when typing

    if (query.length >= 1) {
        $.ajax({
            url: autocompleteUrl,
            data: { term: query },
            dataType: "json",
            success: function (data) {
                suggestionsBox.empty();
                if (data.length > 0) {
                    data.forEach(function (item) {
                        $("<div>")
                            .addClass("suggestion-item")
                            .text(item)
                            .css({
                                padding: "5px",
                                cursor: "pointer",
                                borderBottom: "1px solid #ddd",
                            })
                            .appendTo(suggestionsBox)
                            .on("click", function () {
                                input.val(item);
                                suggestionsBox.hide();
                                // Move focus to next field in the row (unit price)
                                input.closest(".item-row").find(".unit_price").focus();
                            });
                    });
                    suggestionsBox.show();
                } else {
                    suggestionsBox.hide();
                }
            },
        });
    } else {
        suggestionsBox.hide();
    }
});

// ---------------------------------Keyboard navigation with auto-scroll---------------------
$(document).on("keydown", ".item_search_name", function (e) {
    let input = $(this);
    let suggestionsBox = input.siblings(".items_suggestions");
    let items = suggestionsBox.find(".suggestion-item");

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

// Hide dropdown when clicking outside
$(document).on("click", function (e) {
    if (!$(e.target).closest(".item_search_name, .items_suggestions").length) {
        $(".items_suggestions").hide();
    }
});



//          to navigate to a particular sale

async function navigateSale(action) {
  try {
    const currentId = document.getElementById("current_sale_id").value || "";

    // Fetch from Django view
    const response = await fetch(`/sale/get-sale/?action=${action}&current_id=${currentId}`, {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    let data = await response.json();


    // Handle backend errors
    if (data.success === false) {
      Swal.fire({
        icon: "error",
        title: "Oops...",
        text: data.message || "An error occurred!",
      });
      return;
    }

    // Parse JSON string coming from backend
    if (typeof data === "string") {
      data = JSON.parse(data);
    }

    // If Django wrapped the JSON in data.result_data[0] or similar, parse accordingly
    if (typeof data === "object" && data.hasOwnProperty("sales_invoice_id") === false) {
      try {
        data = JSON.parse(Object.values(data)[0]);
      } catch (e) {}
    }

    renderSaleData(data);
  } catch (error) {
    console.error("Error navigating sale:", error);
    Swal.fire({
      icon: "error",
      title: "Error",
      text: "An unexpected error occurred while fetching sale data.",
    });
  }
}

// function renderSaleData(data) {

function renderSaleData(data) {
  // Update header fields
  document.getElementById("search_name").value = data.Party || "";
  document.getElementById("sale_date").value = data.invoice_date || "";
  document.getElementById("current_sale_id").value = data.sales_invoice_id || "";

  // Clear existing items
  const itemsDiv = document.getElementById("items");
  itemsDiv.innerHTML = "";
  // Render each item row in the same structure as addItemRow()
  if (Array.isArray(data.items)) {
    data.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "item-row";
      row.innerHTML = `
        <div class="item_name_field autocomplete-container">
            <input type="text" class="item_name item_search_name" 
                placeholder="Item name" 
                value="${item.item_name || ""}"
                autocomplete="off"
                data-autocomplete-url="${autocompleteItemUrl}">
            <div class="items_suggestions"></div>
        </div>
        <input type="number" class="unit_price" step="0.01" placeholder="Unit price" value="${item.unit_price || 0}">
        <input type="number" class="qty-box" readonly value="${item.qty || 0}">
        <div class="serials"></div>
        <button type="button" class="custom-btn add-serial">+ Serial</button>
        <button type="button" class="custom-btn remove-serial">- Serial</button>
        <button type="button" class="custom-btn remove-item">Remove</button>
      `;

      // Bind button actions (reuse same logic)
      row.querySelector(".add-serial").onclick = () => addSerial(row);
      row.querySelector(".remove-serial").onclick = () => removeSerial(row);
      row.querySelector(".remove-item").onclick = () => { row.remove(); calculateTotal(); };
      row.querySelector(".unit_price").oninput = () => calculateTotal();

      // Append serials
      const serialsDiv = row.querySelector(".serials");
      if (Array.isArray(item.serials)) {
        item.serials.forEach(serial => {
          const input = document.createElement("input");
          input.type = "text";
          input.placeholder = "Serial";
          input.value = serial;
          input.oninput = () => updateQty(row);
          input.onkeydown = (e) => handleEnterKey(e, input);
          serialsDiv.appendChild(input);
        });
      }
      // update button text
      let submitBtn = document.querySelector("#saleForm button[type=submit]");
      if (data.sales_invoice_id) {
          submitBtn.textContent = "Update Sale";
      } else {
          submitBtn.textContent = "Save Sale";
      }

      itemsDiv.appendChild(row);
      updateQty(row);
    });
  }

  // Update total amount
  document.getElementById("totalAmount").textContent =
    data.total_amount ? parseFloat(data.total_amount).toFixed(2) : "0.00";

}


const deleteButton = document.querySelector(".delete-btn");

function confirmDelete(event) {
  event.preventDefault(); // stop the form from submitting immediately

  Swal.fire({
    title: "Are you sure?",
    text: "This sale will be permanently deleted!",
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#d33",
    cancelButtonColor: "#3085d6",
    confirmButtonText: "Yes, delete it!",
    cancelButtonText: "Cancel"
  }).then((result) => {
    if (result.isConfirmed) {
      // ✅ Temporarily remove this listener so the next click doesn’t reopen the alert
      deleteButton.removeEventListener("click", confirmDelete);

      // ✅ Trigger the real submit (calls your buildAndSubmit normally)
      deleteButton.click();

      // ✅ Reattach the listener for next time
      setTimeout(() => {
        deleteButton.addEventListener("click", confirmDelete);
      }, 100);
    }
  });
}

deleteButton.addEventListener("click", confirmDelete);



// // ------------------ Purchase Invoices Summary--------------------------------
// // Generic fetch function for purchase summaries

// ------------------ Purchase Invoices Summary (Enhanced UI) ------------------
async function fetchSaleSummary(from = null, to = null) {
  try {
    let url = "/sale/get-sale-summary/";
    if (from && to) {
      url += `?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
    }

    const response = await fetch(url);
    const data = await response.json();

    if (!data.success && !Array.isArray(data)) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: data.message || "Failed to fetch sale summary.",
      });
      return;
    }

    // ✅ Build the table rows
    let rows = "";
    if (Array.isArray(data) && data.length > 0) {
      data.forEach((sale, idx) => {
        rows += `
          <tr 
            class="sale-row"
            data-vendor="${sale.customer.toLowerCase()}"
            style="cursor:pointer; transition:background 0.2s;"
            onclick="viewSaleDetails(${sale.sales_invoice_id})"
            onmouseover="this.style.background='#f3f4f6';"
            onmouseout="this.style.background='';"
          >
            <td>${idx + 1}</td>
            <td>${sale.sales_invoice_id}</td>
            <td>${sale.invoice_date}</td>
            <td>${sale.customer}</td>
            <td style="text-align:right;">${sale.total_amount.toFixed(2)}</td>
          </tr>`;
      });
    } else {
      rows = `<tr><td colspan="5" style="text-align:center;">No data found</td></tr>`;
    }

    // 🧾 Build styled HTML with search bar
    const htmlContent = `
      <style>
        .sale-container {
          font-family: 'Inter', system-ui, sans-serif;
          max-height: 450px;
          overflow-y: auto;
          padding: 5px;
          border-radius: 8px;
        }
        .sale-search {
          width: 100%;
          padding: 8px 12px;
          margin-bottom: 10px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          outline: none;
          transition: all 0.2s;
        }
        .sale-search:focus {
          border-color: #2563eb;
          box-shadow: 0 0 0 2px rgba(37,99,235,0.1);
        }
        table.sale-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }
        table.sale-table th, table.sale-table td {
          padding: 8px 10px;
          border-bottom: 1px solid #e5e7eb;
        }
        table.sale-table th {
          background: #f9fafb;
          font-weight: 600;
          color: #374151;
        }
        table.sale-table tbody tr:hover {
          background: #f3f4f6;
        }
      </style>

      <input 
        type="text" 
        class="sale-search" 
        placeholder="🔍 Search by Vendor name..." 
        onkeyup="filterSaleTable(this.value)" 
      />

      <div class="sale-container">
        <table class="sale-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Invoice ID</th>
              <th>Date</th>
              <th>Customer</th>
              <th style="text-align:right;">Total Amount</th>
            </tr>
          </thead>
          <tbody id="saleSummaryBody">
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  
    // Helper to temporarily disable background focus
    function disableBackgroundFocus() {
      const inputs = document.querySelectorAll("input, textarea, select, [tabindex]");
      inputs.forEach(el => {
        el.dataset.prevTabindex = el.getAttribute("tabindex");
        el.setAttribute("tabindex", "-1");
      });
    }

    // Restore focus when popup closes
    function enableBackgroundFocus() {
      const inputs = document.querySelectorAll("input, textarea, select, [tabindex]");
      inputs.forEach(el => {
        if (el.dataset.prevTabindex !== undefined) {
          el.setAttribute("tabindex", el.dataset.prevTabindex);
          delete el.dataset.prevTabindex;
        } else {
          el.removeAttribute("tabindex");
        }
      });
    }
    // 🎉 SweetAlert popup
    disableBackgroundFocus();

    Swal.fire({
      title: "📜 Sale Summary",
      html: htmlContent,
      width: "750px",
      confirmButtonText: "Close",
      showConfirmButton: true,
      focusConfirm: false,
      allowOutsideClick: false,
      allowEnterKey: true,
      allowEscapeKey: true,
      didOpen: (popup) => {
        const input = popup.querySelector(".sale-search");

        // 🧠 Stop all background inputs from catching focus events
        document.querySelectorAll("input, textarea, select").forEach(el => {
          el.blur();
        });

        // 🛑 Stop event bubbling that can cause refocus
        popup.addEventListener("focusin", e => e.stopPropagation());
        popup.addEventListener("keydown", e => e.stopPropagation());

        // 🧩 Try multiple ways to force focus after rendering
        setTimeout(() => {
          if (input) {
            input.focus();
            input.select();
            // 👇 Forcefully focus again a bit later in case other scripts interfere
            setTimeout(() => input.focus(), 400);
            setTimeout(() => input.focus(), 800);
          }
        }, 100);
      },

      willClose: () => {
        // Re-enable background focus when popup closes
        enableBackgroundFocus();
      }
    });



  } catch (error) {
    Swal.fire({
      icon: "error",
      title: "Network Error",
      text: error.message || "Unable to fetch sale summary. Please try again!",
    });
  }
}

function filterSaleTable(query) {
  query = query.toLowerCase().trim();
  const rows = document.querySelectorAll("#saleSummaryBody .sale-row");
  rows.forEach(row => {
    const vendor = row.dataset.vendor;
    row.style.display = vendor.includes(query) ? "" : "none";
  });
}

// 🧮 1️⃣ Button: Fetch Last 20 Sales
function saleHistory() {
  fetchSaleSummary();
}

// 📅 2️⃣ Button: Fetch Sales by Date Range
function saleDateWise() {
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
        confirmButtonText: "Fetch Sales",
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

            fetchSaleSummary(fromDate, toDate);
        }
    });
}

// 🔹 New function to handle click on a purchase row
function viewSaleDetails(saleID) {
  document.getElementById("current_sale_id").value = saleID;
  navigateSale("current")
  Swal.close();
}


