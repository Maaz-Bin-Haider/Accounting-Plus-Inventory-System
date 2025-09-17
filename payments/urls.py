from django.urls import path
from .views import make_payment

urlpatterns = [
    path('payment/',make_payment,name="payment")
]