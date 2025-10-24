from django.urls import path
from .views import detailed_ledger_view

app_name = "accountsReports"

urlpatterns = [
    path('detailed-ledger/',detailed_ledger_view, name="detailed_ledger"),
]