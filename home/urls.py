from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path('', views.home_view, name='home'),
    path('api/cash/', views.get_cash_balance, name='get_cash_balance'),
    path('api/parties/', views.get_parties, name='get_parties'),
    path('api/items/', views.get_items, name='get_items'),
    path('api/party-balances/', views.get_party_balances, name='get_party_balances'),
    path('api/expense-party-balances/', views.get_expense_party_balances, name='get_expense_party_balances'),
]