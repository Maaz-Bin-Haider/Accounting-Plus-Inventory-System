from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import connection
from datetime import datetime, date
import json
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def purchasing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get("action")  
            purchase_id = data.get("purchase_id")
            if purchase_id:
                purchase_id = int(purchase_id)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON"})
        
        if action == "submit":
            
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
                        if not purchase_id:
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
                if not purchase_id: # means new Purchase
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
                        return JsonResponse({"success": False, "message": "Failed to make Purchase, try again!"})  
                else: # if purchase ID Exists Means we have to update
                    # Validating If any serial number is removed from updated invoice which is already sold or purchases Returned
                    try:
                        
                        # Prepare your purchase items data
                        items_data = []
                        for item in data.get("items"):
                            items_data.append(item)

                
                        # Convert Python list → JSON string
                        items_json = json.dumps(items_data)
                        
                        
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT validate_purchase_update(%s,%s)",[purchase_id,items_json])
                            result = cursor.fetchone()[0]
                            result = json.loads(result)
                            


                            if not result["is_valid"]:
                                
                                sold_serials = result.get("sold_serials", [])
                                returned_serials = result.get("returned_serials", [])

                                # Build detailed message lines
                                details = []
                                if sold_serials:
                                    details.append(f"• Sold Serials: {', '.join(sold_serials)}")
                                if returned_serials:
                                    details.append(f"• Returned Serials: {', '.join(returned_serials)}")

                                message = (
                                    "Update blocked: some serial numbers you are trying to remove "
                                    "have already been sold or returned to the vendor.\n\n"
                                    + "\n".join(details)
                                )

                                return JsonResponse({
                                    "success": False,
                                    "message": message
                                })
                    except:
                        return JsonResponse({"success": False, "message": "Update Failed Try Again!"})
                    try:
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
                            
                            # Postgres function `update_purchase_invoice`
                            cursor.execute("""
                                SELECT update_purchase_invoice(%s, %s::jsonb, %s, %s);
                            """, [purchase_id, items_json, data.get("party_name"), purchase_date])

                            # Fetch the returned invoice ID
                            invoice_id = cursor.fetchone()[0]
                            return JsonResponse({"success": True, "message": "Update Successfull"})

                    except:
                        return JsonResponse({"success": False, "message": "Failed to Update Purchase, try again!"})  

                    

            except Exception:
                return JsonResponse({"success": False, "message": "Invalid request data!"})

        if action == "delete":
            
            if not purchase_id:
                return JsonResponse({"success": False, "message": "Navigate to Purchase Invoice first!"})
            
            # Validating If any serial number is removed before deleting any invoice which is already sold or purchases Returned
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT validate_purchase_delete(%s)",[purchase_id])
                    result = cursor.fetchone()[0]
                    result = json.loads(result)
                            
                    if not result["is_valid"]:
                        sold_serials = result.get("sold_serials", [])
                        returned_serials = result.get("returned_serials", [])

                        # Build detailed message lines
                        details = []
                        if sold_serials:
                            details.append(f"• Sold Serials: {', '.join(sold_serials)}")
                        if returned_serials:
                            details.append(f"• Returned Serials: {', '.join(returned_serials)}")

                        message = (
                            "Delete blocked: some serial numbers you are trying to remove "
                            "have already been sold or returned to the vendor.\n\n"
                            + "\n".join(details)
                        )

                        return JsonResponse({
                            "success": False,
                            "message": message
                        })
            except:
                return JsonResponse({"success": False, "message": "Failed to Delete Purchase, try again!"})  
            
            # Executing Delete
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT delete_purchase(%s)",[purchase_id])
                    return JsonResponse({"success": True, "message": "Deleted Successfully"})
            except Exception:
                return JsonResponse({"success": False, "message": "Unable to delete this Purchase! Try Again.."})
    return render(request, "purchase_templates/purchasing_template.html")


@login_required
def get_purchase(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        if action == "previous":
            
            if not current_id:
                
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
                return JsonResponse({"success": False, "message": "No Next Purchase Found"})
            
            # Fetching Next purchase data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_next_purchase(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Next Purchase Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Purchase!"})
            
        elif action == "current": # If no action is provided means we have to fetch current purchase ID
            
            # Validating Current purchase ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Purchase Found"})
            
            # Fetching Next purchase data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_current_purchase(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Purchase Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Purchase!"})
        else:
            pass
    except:
        return JsonResponse({"success": False, "message": "Data base Error!"})
    
    # Sending to frontend
    try:
        
        return JsonResponse(result_data[0])
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid purchase data format."})


@login_required
def get_purchase_summary(request):
    try:
        from_date_str = request.GET.get("from")
        to_date_str = request.GET.get("to")

        # if user want purchasing summary in specific dates
        if from_date_str or to_date_str:
            # Validating Dates (must be in correct date format)
            try:
                # Adjust format according to your input (e.g. "YYYY-MM-DD")
                from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
                to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

                # Future Date Restriction
                if from_date > date.today() or to_date > date.today():
                    return JsonResponse({"success": False, "message": "Dates can't be in Future"})

                # Making Date again Str
                from_date = from_date.strftime("%Y-%m-%d")
                to_date = to_date.strftime("%Y-%m-%d")

            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid date. Please enter a valid date in YYYY-MM-DD format."})
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_purchase_summary(%s, %s)",[from_date,to_date])
                    result = cursor.fetchone()
                
                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Purchase Invoices found in the given date range!"})
            except:
                return JsonResponse({"success": False, "message": "Unable fetch Purchase Invoices, Check your Internet Connection!"})
        # if no date is specified then fetch last 20 purchase invoice summary
        else:
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_purchase_summary()")
                    result = cursor.fetchone()
                
                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Purchase Invoices found"})
            except Exception as e:
                
                return JsonResponse({"success": False, "message": "Unable fetch Purchase Invoices, Check your Internet Connection!"})
        
        # now sending to frontend

        try:
            return JsonResponse(result[0], safe=False)
        except Exception as e:
            
            return JsonResponse({"success": False, "message": "Unexpected Error Occured, Please Try again!"})
        

    except Exception:
        return JsonResponse({"success": False, "message": "Invalid purchase data format."})

