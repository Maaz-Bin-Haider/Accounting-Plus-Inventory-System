from django.urls import path


app_name = "receipts"

urlpatterns = [
    path('payment/',make_payment,name="payment"),
    path("payment/get/", get_payment, name="get_payment"),
    path('get-old-payments/',get_old_payments,name="get_old_payments"),
    path('get-payments-date-wise/',get_payments_date_wise,name="get_payments_date_wise"),
]