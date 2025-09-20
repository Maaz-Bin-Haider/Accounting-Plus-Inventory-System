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