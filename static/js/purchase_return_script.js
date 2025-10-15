function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(";").map(c => c.trim());
  for (let c of cookies) {
    if (c.startsWith(name + "=")) return decodeURIComponent(c.split("=")[1]);
  }
  return null;
}

// 🧩 Add Serial Input
function addSerial(autoFocus = true) {
  const serialsDiv = document.getElementById("serials");

  // Create row container
  const row = document.createElement("div");
  row.className = "serial-row";

  // Create item name input (readonly)
  const itemInput = document.createElement("input");
  itemInput.type = "text";
  itemInput.placeholder = "Item Name";
  itemInput.className = "item-input";
  itemInput.readOnly = true;

  // Create item price input (readonly)
  const itemPrice = document.createElement("input");
  itemPrice.type = "text";
  itemPrice.placeholder = "Item Price";
  itemPrice.className = "item-input";
  itemPrice.readOnly = true;


  // Create serial input
  const serialInput = document.createElement("input");
  serialInput.type = "text";
  serialInput.placeholder = "Enter Serial Number";
  serialInput.className = "serial-input";
  serialInput.oninput = updateCount;
  serialInput.onkeydown = handleEnterKey;

  // Add event to handle serial lookup
  serialInput.addEventListener("change", function () {
    const serialValue = serialInput.value.trim();
    if (serialValue) {
      fetch(`/purchaseReturn/lookup/${encodeURIComponent(serialValue)}/`)
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            itemInput.value = data.item_name;
            itemPrice.value = data.item_price;
          } else {
            itemInput.value = "";
            Swal.fire({
              icon: "error",
              title: "Not Found",
              text: data.message || "Serial not found."
            });
          }
        })
        .catch(() => {
          itemInput.value = "";
          Swal.fire({
            icon: "error",
            title: "Error",
            text: "Failed to fetch item for this serial."
          });
        });
    } else {
      itemInput.value = "";
    }
  });

  // Append both inputs to row
  
  row.appendChild(serialInput);
  row.appendChild(itemInput);
  row.appendChild(itemPrice);

  // Append row to main serials container
  serialsDiv.appendChild(row);

  if (autoFocus) serialInput.focus();
  updateCount();
}

// 🧮 Count serials
function updateCount() {
  const serials = Array.from(document.querySelectorAll("#serials input"))
    .map(i => i.value.trim())
    .filter(v => v !== "");
  document.getElementById("totalQty").textContent = serials.length;
}

// 🧭 Handle Enter Key
// function handleEnterKey(e) {
//   if (e.key === "Enter") {
//     e.preventDefault();
//     if (e.target.value.trim()) addSerial();
//   }
// }

function handleEnterKey(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    
    const serialValue = e.target.value.trim();
    if (serialValue) {
      // Trigger 'change' manually to lookup item name
      e.target.dispatchEvent(new Event("change"));
    }

    // Move focus to next serial input
    const inputs = Array.from(document.querySelectorAll(".serial-input"));
    const index = inputs.indexOf(e.target);
    if (index !== -1 && index + 1 < inputs.length) {
      inputs[index + 1].focus();
    }
  }
}

// 🧾 Build Payload & Submit
function submitReturn(event) {
  event.preventDefault();
  const form = event.target;
  const action = form.querySelector('button[type="submit"][clicked="true"]')?.value; 
  console.log("Action:", action);

  const partyName = document.getElementById("search_name").value.trim();
  if (!partyName) {
    Swal.fire({ icon: "warning", title: "Missing Party", text: "Enter a party name first." });
    return;
  }

  let returnDate = document.getElementById("return_date").value;
  if (!returnDate) returnDate = new Date().toISOString().slice(0, 10);

  const serials = Array.from(document.querySelectorAll(".serial-input"))
    .map(i => i.value.trim())
    .filter(v => v);

  if (serials.length === 0) {
    Swal.fire({ icon: "warning", title: "No Serials", text: "Enter at least one serial number." });
    return;
  }

  const payload = {
    return_id: document.getElementById("current_return_id").value || null,
    party_name: partyName,
    return_date: returnDate,
    serials: serials,
    action: action,
  };
  console.log(payload)
  fetch("/purchaseReturn/create-purchase-return/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken()
    },
    body: JSON.stringify(payload)
  })
  .then(async res => {
    const data = await res.json();
    if (data.success) {
      Swal.fire({
        icon: "success",
        title: "Return Saved ✅",
        text: data.message || "Return saved successfully!",
        timer: 1500,
        showConfirmButton: false
      }).then(() => window.location.reload());
    } else {
      Swal.fire({ icon: "error", title: "Error", text: data.message || "Failed to save return." });
    }
  })
  .catch(err => Swal.fire({ icon: "error", title: "Network Error", text: err.message }));
}

// 🪄 Autocomplete for Party Names
$(document).ready(function () {
  let autocompleteUrl = $("#search_name").data("autocomplete-url");
  let selectedIndex = -1;

  $("#search_name").on("input", function () {
    let query = $(this).val();
    let suggestionsBox = $("#suggestions");
    selectedIndex = -1;

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
                .css({ padding: "5px", cursor: "pointer", borderBottom: "1px solid #ddd" })
                .appendTo(suggestionsBox)
                .on("click", function () {
                  $("#search_name").val(party);
                  suggestionsBox.hide();
                  $("#return_date").focus();
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

  // Keyboard Navigation for Autocomplete
  $("#search_name").on("keydown", function (e) {
    let items = $("#suggestions .suggestion-item");
    if (items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % items.length;
      items.removeClass("highlight");
      items.eq(selectedIndex).addClass("highlight")[0].scrollIntoView({ block: "nearest" });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = (selectedIndex - 1 + items.length) % items.length;
      items.removeClass("highlight");
      items.eq(selectedIndex).addClass("highlight")[0].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      items.eq(selectedIndex).trigger("click");
    }
  });

  $(document).on("click", function (e) {
    if (!$(e.target).closest("#search_name, #suggestions").length) $("#suggestions").hide();
  });

  // Initialize with 5 serials
  for (let i = 0; i < 3; i++) addSerial(false);
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("return_date").value = today;
});

// Helper function to get action of Purchase Form
// Track which submit button was clicked
document.querySelectorAll('button[type="submit"]').forEach(btn => {
  btn.addEventListener('click', function () {
    // Remove clicked="true" from all submit buttons first
    document.querySelectorAll('button[type="submit"]').forEach(b => b.removeAttribute('clicked'));
    // Add clicked="true" only to this one
    this.setAttribute('clicked', 'true');
  });
});