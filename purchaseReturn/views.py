from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
import json
from datetime import datetime, date

# Create your views here.

def createPurchaseReturn(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            purchase_return_ID = data.get("return_id")
            if purchase_return_ID:
                purchase_return_ID = int(purchase_return_ID)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON"})
        
        # New or Update Purchase Return
        if action == "submit":
            print("enter")
            # Validating provided data
            try:
                # Validating Party name
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[data.get("party_name").upper()])
                        exists = cursor.fetchone()

                        if not exists:
                            return JsonResponse({"success": False, "message": f"Party with '{data.get("party_name")}' Not exists!"})
                except:
                    return JsonResponse({"success": False, "message": "Invalid Party-Name"})
                
                # Validate purchase_return_date (must be in correct date format)
                try:
                    # Adjust format according to your input (e.g. "YYYY-MM-DD")
                    purchase_return_date = datetime.strptime(data.get("return_date"), "%Y-%m-%d").date()

                    # Future Date Restriction
                    if purchase_return_date > date.today():
                        return JsonResponse({"success": False, "message": "Purchase Return date cannot be in the future."})

                    # Making Date again Str
                    purchase_return_date = purchase_return_date.strftime("%Y-%m-%d")

                except (ValueError, TypeError):
                    return JsonResponse({"success": False, "message": "Invalid date. Please enter a valid date in YYYY-MM-DD format."})
                
                # Validate Serial Numbers
                try:
                    for serial in data.get("serials"):
                        # checking in Current Stock
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])
                                exists = cursor.fetchone()
                                if not exists[0]:
                                    return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
                                
                                cursor.execute("SELECT vendor_name FROM get_serial_number_details(%s)",[serial])

                                # Validating provided party name for serial with actual party name  
                                vendor_name = cursor.fetchone()
                                if not vendor_name[0] == data.get("party_name"):
                                    return JsonResponse({"success": False, "message": f"The serial number '{serial}' was purchased from {vendor_name}, not from {data.get('party_name')}."})
                        except Exception as e:
                            return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
                except:
                    return JsonResponse({"success": False, "message": "Invalid Serial Data!"}) 
                

                
                # Executing Create_purchase_ return function
                try:
                    json_data = json.dumps(data.get("serials"))
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT create_purchase_return(%s,%s)",[data.get('party_name'),json_data])
                    return JsonResponse({"success": True, "message": "Purchase Return Sucessfull"}) 
                except Exception as e:
                    print(e)
                    return JsonResponse({"success": False, "message": f"Unable to Purchase Return, Try Again! {e}"}) 
                
            except:
                pass

        # Delete Purchase Return
        else:
            pass

    return render(request,'purchase_return_templates/purchase_return_template.html')


def purchase_return_lookup(request,serial:str):

    #validating Serial Number
    try:
        serial = str(serial)
    except:
        return JsonResponse({ "success": False, "message":"Invalid Serial Number" })
    
    # checking in Current Stock
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])
            exists = cursor.fetchone()
            if not exists[0]:
                return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
            
            cursor.execute("SELECT item_name FROM get_serial_number_details(%s)",[serial])
            item_name = cursor.fetchone()
    except Exception as e:
        return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
    
    return JsonResponse({ "success": True, "item_name": item_name[0] })
    