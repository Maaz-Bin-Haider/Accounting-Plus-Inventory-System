from django.urls import path
from .views import sales,get_sale,get_sale_summary

app_name = "sale"

urlpatterns = [
    path('sales/',sales,name="sales"),
    path('get-sale/',get_sale,name="get_sale"),
    path('get-sale-summary/',get_sale_summary,name="get_sale_summary"),
]