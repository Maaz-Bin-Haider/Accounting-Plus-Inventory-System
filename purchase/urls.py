from django.urls import path
from .views import purchasing,get_purchase

app_name = "purchase"

urlpatterns = [
    path('purchasing/',purchasing,name="purchasing"),
    path('get-purchase/',get_purchase,name="get_purchase"),
]