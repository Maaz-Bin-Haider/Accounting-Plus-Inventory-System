from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import connection
from datetime import datetime, date
import json

# Create your views here.

def purchasing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(data)
            # validation example
            if not data.get("party_name"):
                return JsonResponse({"success": False, "message": "Party name is required."})
            
            if not data.get("purchase_date"):
                return JsonResponse({"success": False, "message": "Date name is required."})
            
            if not data.get("items"):
                return JsonResponse({"success": False, "message": "Atlest one item is required to make a Purchase"})
            

            # Validating Party name
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[data.get("party_name").upper()])
                exists = cursor.fetchone()

                if not exists:
                    return JsonResponse({"success": False, "message": f"Party with '{data.get("party_name")}' Not exists!"})
                
            # Validate purchase_date (must be in correct date format)
            try:
                # Adjust format according to your input (e.g. "YYYY-MM-DD")
                purchase_date = datetime.strptime(data.get("purchase_date"), "%Y-%m-%d").date()

                # Future Date Restriction
                if purchase_date > date.today():
                    return JsonResponse({"success": False, "message": "Purchase date cannot be in the future."})

                # Making Date again Str
                purchase_date = purchase_date.strftime("%Y-%m-%d")

            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid date. Please enter a valid date in YYYY-MM-DD format."})
            
            try: 
                for item in data.get("items"):
                    item_name = item["item_name"]
                    qty = item["qty"]
                    unit_price = item["unit_price"]
                    serials = item["serials"]

                    # validating item name
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM Items WHERE UPPER(item_name) = %s",[item_name.upper()])
                        exists = cursor.fetchone()

                        if not exists:
                            return JsonResponse({"success": False, "message": f"Item with '{item_name.upper()}' Not exists!"})
                        

            except:
                pass
            
            
            # if data.get("party_name") != 'ff':
            #     return JsonResponse({"success": False, "message": "Party name is required."})

            return JsonResponse({"success": True, "message": "Data loaded successfully"})
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid request data!"})

    return render(request, "purchase_templates/purchasing_template.html")