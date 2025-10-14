from django.urls import path
from .views import createPurchaseReturn

app_name = "purchaseReturn"

urlpatterns = [
    path('create-purchase-return/',createPurchaseReturn, name="create_purchase_return"),
]