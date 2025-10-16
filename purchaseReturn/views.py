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
                

                if not purchase_return_ID:
                    # Executing Create_purchase_ return function
                    try:
                        json_data = json.dumps(data.get("serials"))
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT create_purchase_return(%s,%s)",[data.get('party_name'),json_data])
                        return JsonResponse({"success": True, "message": "Purchase Return Sucessfull"}) 
                    except Exception as e:
                        return JsonResponse({"success": False, "message": f"Unable to Purchase Return, Try Again!"}) 
                else:
                    # Executing update_purchase_ return function
                    try:
                        json_data = json.dumps(data.get("serials"))
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT update_purchase_return(%s,%s)",[purchase_return_ID,json_data])
                        return JsonResponse({"success": True, "message": "Purchase-Return Updated Sucessfully"}) 
                    except Exception as e:
                        print(e)
                        return JsonResponse({"success": False, "message": f"Unable to Update Purchase-Return, Try Again!"})
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
            
            cursor.execute("SELECT item_name,purchase_price FROM get_serial_number_details(%s)",[serial])
            item = cursor.fetchall()
            print(item)
    except Exception as e:
        return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
    
    return JsonResponse({ "success": True, "item_name": item[0][0], "item_price": item[0][1]})
    
def get_purchase_return(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        if action == "previous":
            
            if not current_id:
                
                # getting and  previous purchase return ID
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT get_last_purchase_return_id()")
                        last_purchase_return = cursor.fetchone()
                        
                        if not last_purchase_return or not last_purchase_return[0]:
                            return JsonResponse({"success": False, "message": "No Last Purchase Return!"})
                        
                        try:
                            last_purchase_return = last_purchase_return[0]
    
                            current_id = int(last_purchase_return) + 1
                        except:
                            return JsonResponse({"success": False, "message": "Invalid Last Purchase-Return data!"})
                except:
                    return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Purchase-Return!"})
    
            # Validating Current purchase-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid Previous Purchase-Return ID!"})
            
            # Fetching Previous purchase-return data from DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_previous_purchase_return(%s)",[current_id])
                    result_data = cursor.fetchone()
                 
                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Previous Purchase-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Purchase-Return!"})
        elif action == "next":
            # Validating Current purchase-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Next Purchase-Return Found"})
            
            # Fetching Next purchase-return data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_next_purchase_return(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Next Purchase-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Purchase-Return!"})
            
        elif action == "current": # If no action is provided means we have to fetch current purchase-return ID
            print("Entered in current----")
            # Validating Current purchase-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Purchase-Return Found"})
            
            # Fetching Next purchase-return data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_current_purchase_return(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Purchase-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Purchase-Return!"})
        else:
            pass
    except:
        return JsonResponse({"success": False, "message": "Data base Error!"})
    
    # Sending to frontend
    try:
        print(result_data[0])
        return JsonResponse(result_data[0],safe=False)
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid purchase-return data format."})
