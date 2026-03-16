from django.http import JsonResponse
from django.db import connection
from django.contrib import messages
from django.shortcuts import render,redirect
import json
from django.contrib.auth.decorators import login_required


@login_required
def home_view(request):
    return render(request, "home_templtes/home_template.html")

@login_required
def get_cash_balance(request):
    """Fetch current cash balance from vw_trial_balance (Cash account)."""
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        return JsonResponse({"cash_balance": 0.00})


    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT balance 
            FROM vw_trial_balance 
            WHERE name = 'Cash'
            LIMIT 1;
        """)
        row = cursor.fetchone()
    cash_balance = float(row[0]) if row else 0.0
    return JsonResponse({"cash_balance": cash_balance})

# Retired Function
@login_required
def get_party_balances(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        data= {}
        data = json.loads(data)
        return JsonResponse(data, safe=False)
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_party_balances_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


@login_required
def get_expense_party_balances(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        data= {}
        data = json.loads(data)
        return JsonResponse(data, safe=False)
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_expense_party_balances_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


@login_required
def get_parties(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_parties_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


@login_required
def get_items(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_items_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


@login_required
def get_party_balance_ledger_exclusing_mains(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_party_balances_json_excluding(%s);",[['ABDUL MAJID BHAI', 'ABDUL REHMAN BHAI','FAISAL BHAI','WAHEED BHAI']])
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


@login_required
def get_receivables_exclusing_mains(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_accounts_receivable_json_excluding();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)

@login_required
def get_payables_exclusing_mains(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_accounts_payable_json_excluding(%s);",[['ABDUL MAJID BHAI', 'ABDUL REHMAN BHAI','FAISAL BHAI','WAHEED BHAI']])
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)