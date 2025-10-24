from django.shortcuts import render
from django.db import connection, IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

def detailed_ledger_view(request):

    # ---- (1) Render the template on GET request ----
    if request.method == "GET":
        return render(request, "display_report_templates/detailed_ledger_template.html")

    # ---- (2) Handle AJAX POST request ----
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            party_name = data.get("party_name", "").strip()
            from_date = data.get("from_date")
            to_date = data.get("to_date")

            # Validate input
            if not party_name or not from_date or not to_date:
                return JsonResponse({
                    "error": "Missing required parameters (party_name, from_date, to_date)."
                }, status=400)

            # Ensure valid date format
            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                return JsonResponse({
                    "error": "Invalid date format. Use YYYY-MM-DD."
                }, status=400)

            # ---- Execute Database Function ----
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM detailed_ledger(%s, %s, %s)", [party_name, from_date, to_date])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            # Format result as list of dictionaries
            result = [dict(zip(columns, row)) for row in rows]

            return JsonResponse(result, safe=False)

        except IntegrityError as e:
            return JsonResponse({"error": f"Database integrity error: {str(e)}"}, status=500)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    # ---- (3) Method not allowed ----
    return JsonResponse({"error": "Method not allowed"}, status=405)
