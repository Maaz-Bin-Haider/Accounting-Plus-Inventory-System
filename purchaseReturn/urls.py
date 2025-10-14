from django.urls import path
from .views import createPurchaseReturn,purchase_return_lookup

app_name = "purchaseReturn"

urlpatterns = [
    path('create-purchase-return/',createPurchaseReturn, name="create_purchase_return"),
    path('lookup/<str:serial>/',purchase_return_lookup,name="purchase_return_lookup"),
]