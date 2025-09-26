$(document).ready(function() {
    // console.log("script started ✅");

    // Set default date only if element exists
    let dateInput = document.getElementById("receipt_date");
    if (dateInput) {
        dateInput.valueAsDate = new Date();
        console.log("date set ✅");
    }

    let autocompleteUrl = $("#search_name").data("autocomplete-url");
    console.log("autocomplete URL:", autocompleteUrl);

    $("#search_name").on("input", function() {
        let query = $(this).val();
        console.log("typing:", query);

        let suggestionsBox = $("#suggestions");

        if (query.length >= 1) {
            $.ajax({
                url: autocompleteUrl,
                data: { 'term': query },
                dataType: 'json',
                success: function(data) {
                    console.log("response:", data);
                    suggestionsBox.empty();
                    if (data.length > 0) {
                        data.forEach(function(party) {
                            $("<div>")
                                .text(party)
                                .css({
                                    padding: "5px",
                                    cursor: "pointer",
                                    borderBottom: "1px solid #ddd"
                                })
                                .appendTo(suggestionsBox)
                                .on("click", function() {
                                    $("#search_name").val(party);
                                    suggestionsBox.hide();
                                });
                        });
                        suggestionsBox.show();
                    } else {
                        suggestionsBox.hide();
                    }
                },
                error: function(xhr, status, error) {
                    console.error("AJAX error:", status, error);
                }
            });
        } else {
            suggestionsBox.hide();
        }
    });

    $(document).on("click", function(e) {
        if (!$(e.target).closest("#search_name, #suggestions").length) {
            $("#suggestions").hide();
        }
    });
});



function navigateReceipt(action) {
    let currentId = document.getElementById("current_receipt_id").value;

    fetch(`/receipts/receipt/get/?action=${action}&current_id=${currentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // show message when at boundary
                if (data.info) {
                    alert(data.info);
                }
                return;
            }

            // update form fields
            document.getElementById("receipt_date").value = data.receipt_date || "";
            document.getElementById("search_name").value = data.party_name || "";
            document.getElementById("amount").value = data.amount || "";
            document.getElementById("method").value = data.method || "Cash";
            document.getElementById("description").value = data.description || "";

            // update hidden id
            document.getElementById("current_receipt_id").value = data.receipt_id;

            // update button text
            let submitBtn = document.querySelector("#receiptForm button[type=submit]");
            if (data.receipt_id) {
                submitBtn.textContent = "Update Receipt";
            } else {
                submitBtn.textContent = "Save Receipt";
            }
        })
        .catch(err => console.error("Error:", err));
}

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("receiptForm");
  let confirmedDelete = false; // flag

  form.addEventListener("submit", function (e) {
    const btn = e.submitter; // which button triggered the submit

    if (btn && btn.value === "delete" && !confirmedDelete) {
      e.preventDefault(); // stop normal submission

      Swal.fire({
        title: "Are you sure?",
        text: "This action cannot be undone!",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "Yes, delete it!",
        cancelButtonText: "Cancel"
      }).then((result) => {
        if (result.isConfirmed) {
          confirmedDelete = true;     // mark confirmed
          form.requestSubmit(btn);    // re-trigger submit with same button
        }
      });
    }
  });
});

function fetchReceipts(url) {
    $.ajax({
        url: url,
        type: "GET",
        dataType: "json",
        success: function(response) {
            if (response.length === 0) {
                Swal.fire("No receipts found");
                return;
            }

            let html = `
                <input type="text" id="receiptSearch" placeholder="🔍 Search by Party or Ref #"
                       style="width: 95%; padding: 8px 10px; margin-bottom: 10px;
                              border: 1px solid #ddd; border-radius: 8px; font-size: 14px;">
                <div id="receiptsList" style="max-height: 350px; overflow-y: auto; text-align:left;">
            `;

            let currentDate = null;

            response.forEach((receipt, index) => {
                if (receipt.receipt_date !== currentDate) {
                    currentDate = receipt.receipt_date;
                    html += `
                        <div class="receipt-date-group">
                            <div class="receipt-date-header">${currentDate}</div>
                    `;
                }

                html += `
                    <div class="receipt-row"
                        data-party="${receipt.party_name.toLowerCase()}"
                        data-ref="${(receipt.reference_no || '').toLowerCase()}"
                        data-id="${receipt.receipt_id}">

                        <div class="receipt-top">
                            <span class="receipt-ref">${receipt.reference_no || ""}</span>
                            <span class="receipt-party">${receipt.party_name}</span>
                            <div class="receipt-amount">${receipt.amount}</div>
                        </div>

                        <div class="receipt-tooltip">
                            ${receipt.description || "No description available"}
                        </div>
                    </div>
                `;

                if (receipt === response[response.length - 1] ||
                    response[index + 1]?.receipt_date !== currentDate) {
                    html += `</div>`;
                }
            });

            html += "</div>";

            Swal.fire({
                title: "📑 Receipts",
                html: html,
                width: "650px",
                confirmButtonText: "Close",
                didOpen: () => {
                    const searchBox = document.getElementById("receiptSearch");
                    const rows = document.querySelectorAll(".receipt-row");

                    // 🔎 Search filter
                    searchBox.addEventListener("input", function () {
                        let query = this.value.toLowerCase();
                        rows.forEach(row => {
                            let party = row.getAttribute("data-party");
                            let ref = row.getAttribute("data-ref");
                            row.style.display =
                                (party.includes(query) || ref.includes(query)) ? "flex" : "none";
                        });

                        // Hide empty groups
                        document.querySelectorAll(".receipt-date-group").forEach(group => {
                            const visibleRows = group.querySelectorAll(".receipt-row[style*='display: flex']");
                            group.style.display = visibleRows.length > 0 ? "block" : "none";
                        });
                    });

                    // 🔗 Click handler for rows
                    rows.forEach(row => {
                        row.addEventListener("click", function () {
                            const receiptId = this.getAttribute("data-id");
                            fetch(`/receipts/receipt/get/?current_id=${receiptId}`)
                                .then(response => response.json())
                                .then(data => {
                                    if (data.error) {
                                        // show message when at boundary
                                        if (data.info) {
                                            alert(data.info);
                                        }
                                        return;
                                    }

                                    // Closing the popup before updating form
                                    Swal.close();

                                    // update form fields
                                    document.getElementById("receipt_date").value = data.receipt_date || "";
                                    document.getElementById("search_name").value = data.party_name || "";
                                    document.getElementById("amount").value = data.amount || "";
                                    document.getElementById("method").value = data.method || "Cash";
                                    document.getElementById("description").value = data.description || "";

                                    // update hidden id
                                    document.getElementById("current_receipt_id").value = data.receipt_id;

                                    // update button text
                                    let submitBtn = document.querySelector("#receiptForm button[type=submit]");
                                    if (data.receipt_id) {
                                        submitBtn.textContent = "Update Receipt";
                                    } else {
                                        submitBtn.textContent = "Save Receipt";
                                    }
                                })
                                .catch(err => console.error("Error:", err));

                    
                        });
                    });
                }
            });
        },
        error: function() {
            Swal.fire("Error loading receipts");
        }
    });
}
// Button event to fetch last 20 payments
$("#btnOldReceipts").on("click", function() {
    fetchReceipts("/receipts/get-old-receipts/");
});

// Asking for start and End Dates
$("#btnCustomerReceipts").on("click", function () {
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
        confirmButtonText: "Fetch Receipts",
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

            // Calling fetchPayments functions with dates
            fetchReceipts(`/receipts/get-receipts-date-wise/?from=${fromDate}&to=${toDate}`);
        }
    });
});
