from django.urls import path

app_name = "saleReturn"

urlpatterns = [
    path('create-sale-return/',createPurchaseReturn, name="create_sale_return"),
    path('lookup/<str:serial>/',purchase_return_lookup,name="sale_return_lookup"),
    path('get-sale-return/',get_purchase_return, name="get_sale_return"),
    path('get-sale-return-summary/',get_purchase_return_summary, name="get_sale_return_summary"),
]