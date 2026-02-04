from django.shortcuts import render,redirect
from django.db import connection, IntegrityError
from django.http import JsonResponse
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def detailed_ledger_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/accounts_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            party_name = data.get("party_name", "").strip()
            from_date = data.get("from_date")
            to_date = data.get("to_date")

            if not party_name or not from_date or not to_date:
                return JsonResponse({"error": "Missing required parameters."}, status=400)

            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM detailed_ledger(%s, %s, %s)", [party_name, from_date, to_date])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def trial_balance_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/accounts_reports_template.html")

    elif request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM vw_trial_balance")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def stock_report_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")

    elif request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM stock_report")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def stock_summary(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")
    

    elif request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM stock_summary();")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                print(rows)

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)



@login_required
def stock__worth_report_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")

    elif request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM stock_worth_report")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def item_history_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            item_name = data.get("item_name", "").strip()
            item_name_cap = item_name.upper()

            from_date = data.get("from_date")
            to_date = data.get("to_date")

            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)



            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM item_transaction_history(%s,%s, %s)",[item_name_cap,from_date,to_date])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def item_detail_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            item_name = data.get("item_name", "").strip()
            
            if not item_name:
                return JsonResponse({"error": "Item name is required"}, status=400)
            
            item_name_cap = item_name.upper()

            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_item_stock_by_name(%s)", [item_name_cap])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def company_valuation_report(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/profit_reports_template.html")

    elif request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM standing_company_worth_view")  # or your view call
                row = cursor.fetchone()

            # The function/view returns JSON — parse it if needed
            result_json = row[0] if row else None
            if not result_json:
                return JsonResponse({"error": "No data found."}, status=404)

            return JsonResponse(result_json, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)



@login_required
def sale_wise_report(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/profit_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            from_date = data.get("from_date")
            to_date = data.get("to_date")

            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM sale_wise_profit(%s,%s)",[from_date,to_date])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def serial_ledger_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/stock_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            serial = data.get("serial", "").strip()

            if not serial:
                return JsonResponse({"error": "Serial is required"}, status=400)
            


            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_serial_ledger(%s)", [serial])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()



            result = [dict(zip(columns, row)) for row in rows]


            return JsonResponse(result, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def cash_ledger_view(request):
    if not request.user.has_perm("auth.view_accounts_reports_page"):
        messages.error(request, "Access Denied!")
        return redirect("home:home")
    
    if request.method == "GET":
        return render(request, "display_report_templates/accounts_reports_template.html")

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            from_date = data.get("from_date")
            to_date = data.get("to_date")

            if not from_date or not to_date:
                return JsonResponse({"error": "Missing required date parameters."}, status=400)

            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_cash_ledger_with_party(%s, %s)", [from_date, to_date])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            result = [dict(zip(columns, row)) for row in rows]
            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)