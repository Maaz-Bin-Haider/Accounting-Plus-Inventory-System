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

function addSerial(row) {
  const serialsDiv = row.querySelector(".serials");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Serial";
  input.oninput = () => updateQty(row);
  input.onkeydown = (e) => handleEnterKey(e, input);
  serialsDiv.appendChild(input);
  updateQty(row);
}

function removeSerial(row) {
  const serialsDiv = row.querySelector(".serials");
  if (serialsDiv.lastChild) {
    serialsDiv.removeChild(serialsDiv.lastChild);
    updateQty(row);
  }
}

function addItemRow() {
  const itemsDiv = document.getElementById("items");

  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <input type="text" class="item_name" placeholder="Item name">
    <input type="number" class="unit_price" placeholder="Unit price">
    <input type="number" class="qty-box" readonly value="0">
    <div class="serials"></div>
    <button type="button" class="btn add-serial">+ Serial</button>
    <button type="button" class="btn remove-serial">- Serial</button>
    <button type="button" class="btn remove-item">Remove</button>
  `;

  row.querySelector(".add-serial").onclick = () => addSerial(row);
  row.querySelector(".remove-serial").onclick = () => removeSerial(row);
  row.querySelector(".remove-item").onclick = () => { row.remove(); calculateTotal(); };
  row.querySelector(".unit_price").oninput = () => calculateTotal();

  itemsDiv.appendChild(row);
  enforceSequentialValidation();

  addSerial(row);
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

function buildAndSubmit(event) {
  event.preventDefault();
  const partyName = document.getElementById("party_name").value.trim();
  let purchaseDate = document.getElementById("purchase_date").value;
  if (!purchaseDate) {
    purchaseDate = new Date().toISOString().slice(0,10);
  }
  if (!partyName) {
    alert("Party name is required.");
    document.getElementById("party_name").focus();
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
    alert("Please enter at least one valid item with name, unit price, and serial(s).");
    return;
  }
  const payload = { party_name: partyName, purchase_date: purchaseDate, items: items };
  console.log("Submitting JSON:", JSON.stringify(payload, null, 2));
  alert("Payload:\n" + JSON.stringify(payload, null, 2));
}

window.onload = function() {
  for (let i = 0; i < 3; i++) addItemRow();
  enforceSequentialValidation();
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("purchase_date").value = today;
  document.getElementById("party_name").focus();
};

function handleEnterKey(e, input) {
  if (e.key === "Enter") {
    e.preventDefault();
    if (!input.value.trim()) {
      input.focus();
      return;
    }
    const formInputs = Array.from(document.querySelectorAll("input, select, textarea"));
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
