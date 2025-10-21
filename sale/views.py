from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import connection
from datetime import datetime, date
import json

# Create your views here.

def sales(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get("action")  
            sale_id = data.get("sale_id")
            if sale_id:
                sale_id = int(sale_id)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON"})
        
        if action == "submit":
            print('Entererd')
            try:
                data = json.loads(request.body)
                # validation example
                if not data.get("party_name"):
                    return JsonResponse({"success": False, "message": "Party name is required."})
                
                if not data.get("sale_date"):
                    return JsonResponse({"success": False, "message": "Date name is required."})
                
                if not data.get("items"):
                    return JsonResponse({"success": False, "message": "Atlest one item is required to make a Sale"})
                

                try:
                    # Validating Party name
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[data.get("party_name").upper()])
                        exists = cursor.fetchone()

                        if not exists:
                            return JsonResponse({"success": False, "message": f"Party with '{data.get("party_name")}' Not exists!"})
                except:
                    return JsonResponse({"success": False, "message": "Invalid Party-Name"})

                # Validate sales_date (must be in correct date format)
                try:
                    # Adjust format according to your input (e.g. "YYYY-MM-DD")
                    sale_date = datetime.strptime(data.get("sale_date"), "%Y-%m-%d").date()

                    # Future Date Restriction
                    if sale_date > date.today():
                        return JsonResponse({"success": False, "message": "Sale date cannot be in the future."})

                    # Making Date again Str
                    sale_date = sale_date.strftime("%Y-%m-%d")

                except (ValueError, TypeError):
                    return JsonResponse({"success": False, "message": "Invalid date. Please enter a valid date in YYYY-MM-DD format."})
                
                # Flag for confirmation check when price <= to buying price
                force = data.get("force", False)
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
                        
                        # TODO: Check the give Quantity if this exits in current stock

                        
                        

                        # Validating Serials
                        
                        try:
                            for serial in serials:

                                with connection.cursor() as cursor:
                                    cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])

                                    exists = cursor.fetchone()

                                    if not exists:
                                        return JsonResponse({"success": False, "message": f"The Serial '{serial}' not exists in Stock!"})
                                    
                                    if exists:
                                        cursor.execute("SELECT item_name FROM get_serial_number_details(%s)",[serial])
                                        original_item_name = cursor.fetchone()

                                        # For handling when provided dosen't belongs to the actual item name
                                        try:
                                            if not original_item_name[0] == item_name:
                                                return JsonResponse({"success":False,"message":f"The serial '{serial}' does not belong to {item_name}; it belongs to {original_item_name[0]}."})
                                        except:
                                            return JsonResponse({"success": False, "message": "Invalid Serial Number!"})
                                        
                                        # validating unit price
                                        try:
                                            unit_price = float(unit_price)
                                            if unit_price <= 0:
                                                return JsonResponse({"success": False, "message": "Invalid Price"})
                                            
                                            cursor.execute("SELECT purchase_price FROM get_serial_number_details(%s)",[serial])
                                            buying_price = cursor.fetchone()

                                            try:
                                                if not force:
                                                    if unit_price == float(buying_price[0]):
                                                        return JsonResponse({
                                                            "success": False,
                                                            "confirm": True,
                                                            "message": "The selling price is equal to the buying price. Do you want to continue?"
                                                        })
                                                    elif unit_price < float(buying_price[0]):
                                                        return JsonResponse({
                                                            "success": False,
                                                            "confirm": True,
                                                            "message": "The selling price is less than the buying price. Do you want to continue?"
                                                        })
                                            except Exception as e:
                                                return JsonResponse({"success": False, "message": "Invalid price from database."})
                                            
                                        except:
                                            return JsonResponse({"success": False, "message": "Invalid Price"})

                        except:
                            return JsonResponse({"success": False, "message": "Invalid Serial Number!"})
                        
                except:
                    return JsonResponse({"success": False, "message": "Unexpected Error Please try again!"})
                
                # Execute DB function
                if not sale_id: # means new Sale
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
                            
                            
                            # Prepare your sale items data
                            items_data = []
                            for item in data.get("items"):
                                items_data.append(item)

                    
                            # Convert Python list → JSON string
                            items_json = json.dumps(items_data)

                            # Postgres function `create_purchase`
                            cursor.execute("""
                                SELECT create_sale(%s, %s, %s::jsonb);
                            """, [party_id, sale_date, items_json])

                            # Fetch the returned invoice ID
                            invoice_id = cursor.fetchone()[0]
                            return JsonResponse({"success": True, "message": "Sale Successfull"})
                    except:
                        return JsonResponse({"success": False, "message": "Failed to make Sale, try again!"})  
                else: # if sale ID Exists Means we have to update
                    try:
                        # Prepare your sale items data
                        items_data = []
                        for item in data.get("items"):
                            items_data.append(item)

                
                        # Convert Python list → JSON string
                        items_json = json.dumps(items_data)

                        with connection.cursor() as cursor:
                            cursor.execute("SELECT validate_sales_update(%s,%s)",[sale_id,items_json])
                            result = cursor.fetchone()[0]
                            result = json.loads(result)
                            


                            if not result["is_valid"]:
                                returned_serials = result.get("returned_serials", [])

                                # Build detailed message lines
                                details = []
                                if returned_serials:
                                    details.append(f"• Returned Serials: {', '.join(returned_serials)}")

                                message = (
                                    "Update blocked: some serial numbers you are trying to remove "
                                    "have already been returned from Customer.\n\n"
                                    + "\n".join(details)
                                )

                                return JsonResponse({
                                    "success": False,
                                    "message": message
                                })
                    except:
                        JsonResponse({"success": False, "message": "Unable Update Sale, try again!"})

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
                            
                            
                            # Prepare your sale items data
                            items_data = []
                            for item in data.get("items"):
                                items_data.append(item)

                    
                            # Convert Python list → JSON string
                            items_json = json.dumps(items_data)
                            # print(items_json)
                            # print(type(items_json))

                            # Postgres function `update_purchase_invoice`
                            cursor.execute("""
                                SELECT update_sale_invoice(%s, %s::jsonb, %s, %s);
                            """, [sale_id, items_json, data.get("party_name"), sale_date])

                            # Fetch the returned invoice ID
                            invoice_id = cursor.fetchone()[0]
                            return JsonResponse({"success": True, "message": "Update Successfull"})

                    except:
                        return JsonResponse({"success": False, "message": "Failed to Update Sale, try again!"})  

                    

            except Exception:
                return JsonResponse({"success": False, "message": "Invalid request data!"})

        if action == "delete":
            print("DELETE")
            if not sale_id:
                return JsonResponse({"success": False, "message": "Navigate to Sale Invoice first!"})
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT validate_sales_delete(%s)",[sale_id])
                    result = cursor.fetchone()[0]
                    result = json.loads(result)
                            
                    if not result["is_valid"]:
                        returned_serials = result.get("returned_serials", [])

                        # Build detailed message lines
                        details = []
                        if returned_serials:
                            details.append(f"• Returned Serials: {', '.join(returned_serials)}")

                        message = (
                            "Delete blocked: some serial numbers you are trying to remove "
                            "have already been returned from the Customer.\n\n"
                            + "\n".join(details)
                        )

                        return JsonResponse({
                            "success": False,
                            "message": message
                        })
            except:
                return JsonResponse({"success": False, "message": "Failed to Delete Sale, try again!"})
            
            # Executing Delete
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT delete_sale(%s)",[sale_id])
                    return JsonResponse({"success": True, "message": "Deleted Successfully"})
            except Exception:
                return JsonResponse({"success": False, "message": "Unable to delete this Sale! Try Again.."})
    return render(request, "sale_templates/sale_template.html")


def get_sale(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        if action == "previous":
            if not current_id:
                # getting   previous sale ID
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT get_last_sale_id()")
                        last_sale = cursor.fetchone()
                        
                        if not last_sale or not last_sale[0]:
                            return JsonResponse({"success": False, "message": "No Last Sale!"})
                        
                        try:
                            last_sale = last_sale[0]
    
                            current_id = int(last_sale) + 1
                        except:
                            return JsonResponse({"success": False, "message": "Invalid Last Sale data!"})
                except:
                    return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Sale!"})
    
            # Validating Current Sale ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid Previous Sale ID!"})
            
            # Fetching Previous Sale data from DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_previous_sale(%s)",[current_id])
                    result_data = cursor.fetchone()
                 
                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Previous Sale Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Sale!"})
        elif action == "next":
            # Validating Current sale ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Next Sale Found"})
            
            # Fetching Next sale data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_next_sale(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Next Sale Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Sale!"})
            
        elif action == "current": # If no action is provided means we have to fetch current Sale ID
            print("Entered in current----")
            # Validating Current sale ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Sale Found"})
            
            # Fetching Next sale data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_current_sale(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Sale Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Sale!"})
        else:
            pass
    except:
        return JsonResponse({"success": False, "message": "Data base Error!"})
    
    # Sending to frontend
    try:
        print(result_data[0])
        return JsonResponse(result_data[0])
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid sale data format."})
    

def get_sale_summary(request):
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
                    cursor.execute("SELECT get_sales_summary(%s, %s)",[from_date,to_date])
                    result = cursor.fetchone()
                
                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Sale Invoices found in the given date range!"})
            except:
                return JsonResponse({"success": False, "message": "Unable fetch Sale Invoices, Check your Internet Connection!"})
        # if no date is specified then fetch last 20 sale invoice summary
        else:
            print("Entered Else BLock----")
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_sales_summary()")
                    result = cursor.fetchone()
                print(result[0])
                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Sale Invoices found"})
            except Exception as e:
                print(e)
                return JsonResponse({"success": False, "message": "Unable fetch Sale Invoices, Check your Internet Connection!"})
        
        # now sending to frontend

        try:
            return JsonResponse(result[0], safe=False)
        except Exception as e:
            print(e)
            return JsonResponse({"success": False, "message": "Unexpected Error Occured, Please Try again!"})
        

    except Exception:
        return JsonResponse({"success": False, "message": "Invalid sale data format."})