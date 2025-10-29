$(document).ready(function() {
    // Set default date only if element exists
    let dateInput = document.getElementById("payment_date");
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }

    let autocompleteUrl = $("#search_name").data("autocomplete-url");
    let selectedIndex = -1; // For keyboard navigation

    $("#search_name").on("input", function() {
        let query = $(this).val();
        let suggestionsBox = $("#suggestions");
        selectedIndex = -1; // reset selection when typing

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
                                .addClass("suggestion-item")
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

    // ✅ Keyboard navigation and auto-select
    $("#search_name").on("keydown", function(e) {
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

    // Hide dropdown when clicking outside
    $(document).on("click", function(e) {
        if (!$(e.target).closest("#search_name, #suggestions").length) {
            $("#suggestions").hide();
        }
    });
});



function navigatePayment(action) {
    let currentId = document.getElementById("current_payment_id").value || '';
    console.log(currentId);

    fetch(`/payments/payment/get/?action=${action}&current_id=${currentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // show message when at boundary
                if (action === "previous") {
                    Swal.fire({
                        title: "Notice",
                        text: "No previous record found.",
                        icon: "info",
                        confirmButtonColor: '#3085d6',
                        confirmButtonText: 'OK'
                    });
                } else if (action === "next") {
                    Swal.fire({
                        title: "Notice",
                        text: "No next record found.",
                        icon: "info",
                        confirmButtonColor: '#3085d6',
                        confirmButtonText: 'OK'
                    });
                } else if (data.info) {
                    // fallback for other info messages
                    Swal.fire({
                        title: "Notice",
                        text: data.info,
                        icon: "info",
                        confirmButtonColor: '#3085d6',
                        confirmButtonText: 'OK'
                    });
                }
                return;
            }

            // update form fields
            document.getElementById("payment_date").value = data.payment_date || "";
            document.getElementById("search_name").value = data.party_name || "";
            document.getElementById("amount").value = data.amount || "";
            document.getElementById("method").value = data.method || "Cash";
            document.getElementById("description").value = data.description || "";

            // update hidden id
            document.getElementById("current_payment_id").value = data.payment_id;

            // update button text
            let submitBtn = document.querySelector("#paymentForm button[type=submit]");
            if (data.payment_id) {
                submitBtn.textContent = "Update Payment";
            } else {
                submitBtn.textContent = "Save Payment";
            }
        })
        .catch(err => console.error("Error:", err));
}

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("paymentForm");
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

function fetchPayments(url) {
    $.ajax({
        url: url,
        type: "GET",
        dataType: "json",
        success: function(response) {
            if (response.length === 0) {
                Swal.fire("No payments found");
                return;
            }

            let html = `
                <input type="text" id="paymentSearch" placeholder="🔍 Search by Party or Ref #"
                       style="width: 95%; padding: 8px 10px; margin-bottom: 10px;
                              border: 1px solid #ddd; border-radius: 8px; font-size: 14px;">
                <div id="paymentsList" style="max-height: 350px; overflow-y: auto; text-align:left;">
            `;

            let currentDate = null;

            response.forEach((payment, index) => {
                if (payment.payment_date !== currentDate) {
                    currentDate = payment.payment_date;
                    html += `
                        <div class="payment-date-group">
                            <div class="payment-date-header">${currentDate}</div>
                    `;
                }

                html += `
                    <div class="payment-row"
                        data-party="${payment.party_name.toLowerCase()}"
                        data-ref="${(payment.reference_no || '').toLowerCase()}"
                        data-id="${payment.payment_id}">

                        <div class="payment-top">
                            <span class="payment-ref">${payment.reference_no || ""}</span>
                            <span class="payment-party">${payment.party_name}</span>
                            <div class="payment-amount">${payment.amount}</div>
                        </div>

                        <div class="payment-tooltip">
                            ${payment.description || "No description available"}
                        </div>
                    </div>
                `;

                if (payment === response[response.length - 1] ||
                    response[index + 1]?.payment_date !== currentDate) {
                    html += `</div>`;
                }
            });

            html += "</div>";

            Swal.fire({
                title: "📑 Payments",
                html: html,
                width: "650px",
                confirmButtonText: "Close",
                didOpen: () => {
                    const searchBox = document.getElementById("paymentSearch");
                    const rows = document.querySelectorAll(".payment-row");

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
                        document.querySelectorAll(".payment-date-group").forEach(group => {
                            const visibleRows = group.querySelectorAll(".payment-row[style*='display: flex']");
                            group.style.display = visibleRows.length > 0 ? "block" : "none";
                        });
                    });

                    // 🔗 Click handler for rows
                    rows.forEach(row => {
                        row.addEventListener("click", function () {
                            const paymentId = this.getAttribute("data-id");
                            fetch(`/payments/payment/get/?current_id=${paymentId}`)
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
                                    document.getElementById("payment_date").value = data.payment_date || "";
                                    document.getElementById("search_name").value = data.party_name || "";
                                    document.getElementById("amount").value = data.amount || "";
                                    document.getElementById("method").value = data.method || "Cash";
                                    document.getElementById("description").value = data.description || "";

                                    // update hidden id
                                    document.getElementById("current_payment_id").value = data.payment_id;

                                    // update button text
                                    let submitBtn = document.querySelector("#paymentForm button[type=submit]");
                                    if (data.payment_id) {
                                        submitBtn.textContent = "Update Payment";
                                    } else {
                                        submitBtn.textContent = "Save Payment";
                                    }
                                })
                                .catch(err => console.error("Error:", err));

                    
                        });
                    });
                }
            });
        },
        error: function() {
            Swal.fire("Error loading payments");
        }
    });
}
// Button event to fetch last 20 payments
$("#btnOldPayments").on("click", function() {
    fetchPayments("/payments/get-old-payments/");
});

// Asking for start and End Dates
$("#btnVendorPayments").on("click", function () {
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
        confirmButtonText: "Fetch Payments",
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
            fetchPayments(`/payments/get-payments-date-wise/?from=${fromDate}&to=${toDate}`);
        }
    });
});


// ===========================
// 🔽 Global Keyboard Navigation
// ===========================
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("paymentForm");

    if (!form) return;

    const focusableElements = form.querySelectorAll(
        "input:not([type=hidden]):not([readonly]), textarea, select, button"
    );

    form.addEventListener("keydown", function (e) {
        const key = e.key;
        const activeElement = document.activeElement;

        // Skip navigation if suggestions box is open and visible
        const suggestionsVisible = $("#suggestions:visible").length > 0;
        if (suggestionsVisible && (key === "ArrowDown" || key === "ArrowUp" || key === "Enter")) {
            return; // let autocomplete handle it
        }

        // Find current index in focusable list
        const index = Array.from(focusableElements).indexOf(activeElement);
        if (index === -1) return;

        // Enter or ArrowDown → move to next input
        if (key === "Enter" || key === "ArrowDown") {
            e.preventDefault();
            const next = focusableElements[index + 1];
            if (next) next.focus();
        }

        // ArrowUp → move to previous input
        else if (key === "ArrowUp") {
            e.preventDefault();
            const prev = focusableElements[index - 1];
            if (prev) prev.focus();
        }
    });
});

