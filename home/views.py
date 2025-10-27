from django.http import JsonResponse
from django.db import connection
from django.shortcuts import render
import json


def home_view(request):
    return render(request, "home_templtes/home_template.html")


def get_cash_balance(request):
    """Fetch current cash balance from vw_trial_balance (Cash account)."""
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


def get_party_balances(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_party_balances_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


def get_expense_party_balances(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_expense_party_balances_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


def get_parties(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_parties_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)


def get_items(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_items_json();")
        data = cursor.fetchone()[0]
        data = json.loads(data)
    return JsonResponse(data, safe=False)
