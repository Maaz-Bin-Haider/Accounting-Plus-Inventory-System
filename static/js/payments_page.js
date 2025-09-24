$(document).ready(function() {
    console.log("script started ✅");

    // Set default date only if element exists
    let dateInput = document.getElementById("payment_date");
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



function navigatePayment(action) {
    let currentId = document.getElementById("current_payment_id").value;

    fetch(`/payments/payment/get/?action=${action}&current_id=${currentId}`)
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

function fetchOldPayments() {
    $.ajax({
        url: "/payments/get-old-payments/",
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
                title: "📑 Last Payments",
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
// Button event
$("#togglePaymentsBtn").on("click", function() {
    fetchOldPayments();
});
