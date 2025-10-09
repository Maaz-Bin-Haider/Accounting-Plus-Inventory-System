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
            # validation example
            if not data.get("party_name"):
                return JsonResponse({"success": False, "message": "Party name is required."})
            
            if not data.get("purchase_date"):
                return JsonResponse({"success": False, "message": "Date name is required."})
            
            if not data.get("items"):
                return JsonResponse({"success": False, "message": "Atlest one item is required to make a Purchase"})
            

            try:
                # Validating Party name
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[data.get("party_name").upper()])
                    exists = cursor.fetchone()

                    if not exists:
                        return JsonResponse({"success": False, "message": f"Party with '{data.get("party_name")}' Not exists!"})
            except:
                return JsonResponse({"success": False, "message": "Invalid Party-Name"})

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


                    # validating item name
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT 1 FROM Items WHERE UPPER(item_name) = %s",[item_name.upper()])
                            exists = cursor.fetchone()

                            if not exists:
                                return JsonResponse({"success": False, "message": f"Item with '{item_name.upper()}' Not exists!"})
                    except:
                        return JsonResponse({"success": False, "message": "Invalid Item-name"})

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
                return JsonResponse({"success": False, "message": "Unexpected Error Please try again!"})
            
            # Execute DB function
            try:
                # Find the vendor ID
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

                    # Fetch the returned invoice ID
                    invoice_id = cursor.fetchone()[0]
                    return JsonResponse({"success": True, "message": "Purchase Successfull"})
            except:
                return JsonResponse({"success": False, "message": "Failed to make Payment, try again!"})   
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid request data!"})

    return render(request, "purchase_templates/purchasing_template.html")

def get_purchase(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")

    

    try:
        if action == "previous":
            
            if not current_id:
                print('ENter')
                # getting and  previous purchase ID
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT get_last_purchase_id()")
                        last_purchase = cursor.fetchone()
                        
                        if not last_purchase or not last_purchase[0]:
                            return JsonResponse({"success": False, "message": "No Last Purchase!"})
                        
                        try:
                            last_purchase = last_purchase[0]
    
                            current_id = int(last_purchase) + 1
                        except:
                            return JsonResponse({"success": False, "message": "Invalid Last Purchase data!"})
                except:
                    return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Purchase!"})
    
            # Validating Current purchase ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid Previous Purchase ID!"})
            
            # Fetching Previous purchase data from DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_previous_purchase(%s)",[current_id])
                    result_data = cursor.fetchone()
                 
                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Previous Purchase Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Purchase!"})
        elif action == "next":
            # Validating Current purchase ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid Previous Purchase ID!"})
            
            # Fetching Next purchase data from DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_next_purchase(%s)",[current_id])
                    result_data = cursor.fetchone()
                if not result_data or result_data[0]:
                    return JsonResponse({"success": False, "message": "No Next Purchase Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Purchase!"})
            
        else:
            pass

    except:
        return JsonResponse({"success": False, "message": "Data base Error!"})
    
    # Sending to frontend
    try:
        print(result_data[0])
        return JsonResponse(json.dumps(result_data[0]))
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid purchase data format."})


# TODO:
# item addition sale price float error handling