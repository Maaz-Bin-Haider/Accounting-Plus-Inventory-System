from django.urls import path
from .views import detailed_ledger_view, trial_balance_view,stock_report_view,stock__worth_report_view,item_history_view

app_name = "accountsReports"

urlpatterns = [
    path('detailed-ledger/',detailed_ledger_view, name="detailed_ledger"),
    path('trial-balance/',trial_balance_view, name="trial_balance"),
    path('stock-report/',stock_report_view,name="stock_report"),
    path('stock-worth-report/',stock__worth_report_view,name="stock__worth_report"),
    path('item-history/',item_history_view,name="item_history"),
]