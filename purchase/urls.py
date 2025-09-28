from django.urls import path
from .views import purchasing

app_name = "purchase"

urlpatterns = [
    path('purchasing/',purchasing,name="purchasing"),
]