from django.urls import path
from .views import make_payment,get_payment

app_name = "payments"

urlpatterns = [
    path('payment/',make_payment,name="payment"),
    path("payment/get/", get_payment, name="get_payment"),
]