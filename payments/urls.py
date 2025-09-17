from django.urls import path
from .views import make_payment

app_name = "payments"

urlpatterns = [
    path('payment/',make_payment,name="payment"),
]