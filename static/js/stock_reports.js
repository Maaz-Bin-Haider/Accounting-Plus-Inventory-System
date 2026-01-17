function getCSRFToken(){
  const name = "csrftoken=";
  const parts = decodeURIComponent(document.cookie).split(";");
  for (let p of parts){
    p = p.trim();
    if (p.startsWith(name)) return p.substring(name.length);
  }
  return "";
}

// ---------- SELECT REPORT ----------
// function selectReport(type){
//   $(".report-btn").removeClass("active");
//   $(`#btn-${type}`).addClass("active");

//   $("#reportHeader").empty();
//   $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);

//   // Hide or show form section
//   const $formSection = $("#report-form-container");
//   if (type === "history") {
//     renderHistoryForm();
//   } else {
//     $formSection.empty();  // hide input fields for stock/worth
//     fetchReport(
//       type === "stock" 
//         ? "/accountsReports/stock-report/"
//         : "/accountsReports/stock-worth-report/"
//     );
//   }
// }

function selectReport(type){
  $(".report-btn").removeClass("active");
  $(`#btn-${type}`).addClass("active");

  $("#reportHeader").empty();
  $("#reportBody").html(`<tr><td class="no-data">Loading...</td></tr>`);

  const $formSection = $("#report-form-container");

  if (type === "history") {
      renderHistoryForm();
  } 
  else if (type === "serial") {   // ✅ add this
      renderSerialForm();
  }
  else if (type === "summary") {
      renderStockSummary();
  }
  else {
      $formSection.empty();
      fetchReport(
        type === "stock"
        ? "/accountsReports/stock-report/"
        : "/accountsReports/stock-worth-report/"
      );
  }
}



// ---------- FETCH GENERIC REPORT ----------
function renderStockSummary(){
  console.log("callesd");
  Swal.fire({ title: "Loading...", didOpen: () => Swal.showLoading(), allowOutsideClick: false });
  fetch("/accountsReports/stock-summary/", {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRFToken": getCSRFToken()}
  })
  .then(r => r.json())
  .then(data => {
    Swal.close();
    if (data.error) return Swal.fire("Error", data.error, "error");
    renderTable(data);
  })
  .catch(() => Swal.fire("Error", "Unable to fetch data", "error"));
}


// ---------- RENDER ITEM HISTORY FORM ----------
function renderHistoryForm(){
  const today = new Date().toISOString().split("T")[0];
  const html = `
    <div class="form-row">
      <div class="autocomplete-container">
        <label>Item Name</label><br>
        <input type="text" id="item_name" placeholder="Enter item name" autocomplete="off"
               data-autocomplete-url="${window.ITEM_AUTOCOMPLETE_URL}">
        <div id="suggestions"></div>
      </div>
    </div>
    <div class="form-row-inline">
      <div class="date-group">
        <label>From:</label>
        <input type="date" id="from_date" value="2000-01-01">
      </div>
      <div class="date-group">
        <label>To:</label>
        <input type="date" id="to_date" value="${today}">
      </div>
      <button class="generate-btn" onclick="fetchItemHistory()">Generate</button>
    </div>`;
  
  $("#report-form-container").html(html);
  $("#reportHeader").empty();
  $("#reportBody").html(`<tr><td class="no-data">Enter item name and date range</td></tr>`);
  initAutocomplete();
}


function renderSerialForm() {
  const html = `
    <div class="form-row">
      <div>
        <label>Serial No</label><br>
        <input type="text" id="serial_input" placeholder="Enter Serial e.g. IP15-001">
      </div>
      <button class="generate-btn" onclick="fetchSerialLedger()">Generate</button>
    </div>
  `;

  $("#report-form-container").html(html);
  $("#reportHeader").empty();
  $("#reportBody").html(`<tr><td class="no-data">Enter serial and click generate</td></tr>`);
}


// ---------- FETCH GENERIC REPORT ----------
function fetchReport(url){
  Swal.fire({ title: "Loading...", didOpen: () => Swal.showLoading(), allowOutsideClick: false });
  fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRFToken": getCSRFToken()}
  })
  .then(r => r.json())
  .then(data => {
    Swal.close();
    if (data.error) return Swal.fire("Error", data.error, "error");
    renderTable(data);
  })
  .catch(() => Swal.fire("Error", "Unable to fetch data", "error"));
}

// ---------- FETCH ITEM HISTORY ----------
function fetchItemHistory(){
  const item = $("#item_name").val().trim();
  const from = $("#from_date").val();
  const to = $("#to_date").val();
  if (!item) return Swal.fire("Missing Item", "Please enter an item name", "warning");

  Swal.fire({ title: "Loading item history...", didOpen: ()=> Swal.showLoading(), allowOutsideClick:false });

  fetch("/accountsReports/item-history/", {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    body: JSON.stringify({ item_name: item, from_date: from, to_date: to })
  })
  .then(r => r.json())
  .then(data => {
    Swal.close();
    if (data.error) return Swal.fire("Error", data.error, "error");
    renderTable(data);
  })
  .catch(()=> Swal.fire("Error", "Unable to fetch item history", "error"));
}


function fetchSerialLedger(){
  const serial = $("#serial_input").val().trim();
  if (!serial) return Swal.fire("Missing Serial", "Please enter a serial", "warning");

  Swal.fire({title:"Loading serial ledger...", didOpen:()=>Swal.showLoading(), allowOutsideClick:false});

  fetch("/accountsReports/serial-ledger/", {
    method: "POST",
    headers: { "Content-Type":"application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify({ serial })
  })
  .then(r => r.json())
  .then(data => {
    Swal.close();
    if (data.error) return Swal.fire("Error", data.error, "error");
    renderTable(data);
  })
  .catch(() => Swal.fire("Error", "Unable to fetch serial ledger", "error"));
}


// ---------- RENDER TABLE ----------
function renderTable(data){
  const header = $("#reportHeader"), body = $("#reportBody");
  if (!data || !data.length){
    header.empty(); body.html(`<tr><td class="no-data">No records found</td></tr>`); return;
  }
  const cols = Object.keys(data[0]);
  header.html(`<tr>${cols.map(c=>`<th>${c.replace(/_/g," ")}</th>`).join("")}</tr>`);
  body.html(data.map(row => 
    `<tr>${cols.map(c=>`<td>${row[c] ?? ""}</td>`).join("")}</tr>`).join(""));
}

// ---------- PDF DOWNLOAD ----------
$(document).on("click","#download_pdf", function(){
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p","pt","a4");
  doc.setFontSize(14);
  doc.text("Stock Report", 40, 40);
  doc.autoTable({ html: "#reportTable", startY: 60, theme:"grid", styles:{fontSize:9} });
  const pages = doc.internal.getNumberOfPages();
  for(let i=1;i<=pages;i++){
    doc.setPage(i);
    doc.setFontSize(8);
    doc.text(`Page ${i} of ${pages}`, doc.internal.pageSize.width - 60, doc.internal.pageSize.height - 20);
  }
  doc.save(`stock_report_${new Date().toISOString().split("T")[0]}.pdf`);
});

// ---------- AUTOCOMPLETE ----------
function initAutocomplete(){
  const $input = $("#item_name"), $box = $("#suggestions");
  const url = $input.data("autocomplete-url");
  let index = -1, items = [];

  $input.off(".auto").on("input.auto", function(){
    const q = $(this).val();
    index = -1; items = []; $box.empty();
    if (!q) return $box.hide();

    $.getJSON(url, { term: q }, function(data){
      items = data || [];
      $box.empty();
      if (!items.length) return $box.hide();
      items.forEach((t,i)=>{
        $("<div>").addClass("suggestion-item").text(t)
        .on("click", ()=>{ $input.val(t); $box.hide(); })
        .appendTo($box);
      });
      $box.show();
    });
  });

  $input.on("keydown.auto", function(e){
    const $it = $box.children(".suggestion-item");
    if (e.key === "ArrowDown"){ e.preventDefault(); if ($it.length) index = (index+1)%$it.length; }
    if (e.key === "ArrowUp"){ e.preventDefault(); if ($it.length) index = (index-1+$it.length)%$it.length; }
    $it.removeClass("highlight").eq(index).addClass("highlight");

    if (e.key === "Enter"){
      e.preventDefault();
      if (items.length === 1) { $input.val(items[0]); $box.hide(); }
      else if (index >= 0) { $input.val($it.eq(index).text()); $box.hide(); }
    }
    if (e.key === "Escape") $box.hide();
  });

  $(document).on("click.auto", e=>{
    if(!$(e.target).closest("#item_name,#suggestions").length) $box.hide();
  });
}

// ---------- INIT ----------
$(document).ready(()=> selectReport("history"));
