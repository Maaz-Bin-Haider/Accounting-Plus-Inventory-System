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
            # print(data)
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
            
            # validate Items
            try: 
                for item in data.get("items"):
                    item_name = item["item_name"]
                    qty = item["qty"]
                    unit_price = item["unit_price"]
                    serials = item["serials"]

                    print(qty,type(qty))
                    print(unit_price,type(unit_price))
                    print(serials,type(serials))

                    # validating item name
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM Items WHERE UPPER(item_name) = %s",[item_name.upper()])
                        exists = cursor.fetchone()

                        if not exists:
                            return JsonResponse({"success": False, "message": f"Item with '{item_name.upper()}' Not exists!"})
                        
                    # validating quantity 
                    try:
                        qty = int(qty)
                        if qty <= 0:
                            return JsonResponse({"success": False, "message": "Invalid Quantity"})
                    except:
                        return JsonResponse({"success": False, "message": "Invalid Quantity"})

                    # validating unit price
                    try:
                        unit_price = float(unit_price)
                        if unit_price <= 0:
                            return JsonResponse({"success": False, "message": "Invalid Price"})
                    except:
                        return JsonResponse({"success": False, "message": "Invalid Price"})
                    

                    # Validating Serials
                    try:
                        for serial in serials:

                            with connection.cursor() as cursor:
                                cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])

                                exists = cursor.fetchone()

                                if exists:
                                    return JsonResponse({"success": False, "message": f"The Serial '{serial}' already exists in Stock!"})
                    except:
                        return JsonResponse({"success": False, "message": "Invalid Serial Number!"})
                    
            except:
                pass
            
            # Execute DB function
            try:
                print('Enter Execution Block------')
                # 1️⃣ Find the vendor ID
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT party_id 
                        FROM Parties 
                        WHERE party_name = %s
                    """, [data.get("party_name")])
                    result = cursor.fetchone()
                    if not result:
                        return JsonResponse({"success": False, "message": f"Party '{data.get("party_name")}' not found in Parties."})
                    party_id = result[0]
                    
                    
                    # Prepare your purchase items data
                    items_data = []
                    for item in data.get("items"):
                        items_data.append(item)

            
                    # Convert Python list → JSON string
                    items_json = json.dumps(items_data)

                    # Postgres function `create_purchase`
                    cursor.execute("""
                        SELECT create_purchase(%s, %s, %s::jsonb);
                    """, [party_id, purchase_date, items_json])

                    # 4️⃣ Fetch the returned invoice ID
                    invoice_id = cursor.fetchone()[0]
                    return JsonResponse({"success": True, "message": "Purchase Successfull"})
            except:
                pass
            

            return JsonResponse({"success": True, "message": "Data loaded successfully"})
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid request data!"})

    return render(request, "purchase_templates/purchasing_template.html")