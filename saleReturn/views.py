from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
import json
from datetime import datetime, date

# Create your views here.

def createSaleReturn(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            sale_return_ID = data.get("return_id")
            if sale_return_ID:
                sale_return_ID = int(sale_return_ID)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON"})
        
        # New or Update Sale Return
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
                
                # Validate sale_return_date (must be in correct date format)
                try:
                    # Adjust format according to your input (e.g. "YYYY-MM-DD")
                    sale_return_date = datetime.strptime(data.get("return_date"), "%Y-%m-%d").date()

                    # Future Date Restriction
                    if sale_return_date > date.today():
                        return JsonResponse({"success": False, "message": "Sale Return date cannot be in the future."})

                    # Making Date again Str
                    sale_return_date = sale_return_date.strftime("%Y-%m-%d")

                except (ValueError, TypeError):
                    return JsonResponse({"success": False, "message": "Invalid date. Please enter a valid date in YYYY-MM-DD format."})
                
                # Validate Serial Numbers
                try:
                    for serial in data.get("serials"):
                        # checking in Current Stock
                        try:
                            # Skipping when updating a purchase return invoice
                            if sale_return_ID:
                                with connection.cursor() as cursor:
                                    cursor.execute("SELECT serial_exists_in_sales_return(%s,%s)",[sale_return_ID,serial])
                                    exists = cursor.fetchone()

                                    if exists:
                                        continue

                            with connection.cursor() as cursor:
                                cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])
                                exists = cursor.fetchone()
                                if exists[0]:
                                    return JsonResponse({ "success": False, "message":f"The Serial '{serial}' already exists in stock!" })
                                
                                cursor.execute("SELECT customer_name FROM get_serial_number_details(%s)",[serial])

                                # Validating provided party name for serial with actual party name  
                                customer_name = cursor.fetchone()
                                if not customer_name[0] == data.get("party_name"):
                                    return JsonResponse({"success": False, "message": f"The serial number '{serial}' was sold to {customer_name}, not to {data.get('party_name')}."})
                        except Exception as e:
                            return JsonResponse({ "success": False, "message":f"The Serial '{serial}' is Invalid!" })
                except:
                    return JsonResponse({"success": False, "message": "Invalid Serial Data!"}) 
                

                if not sale_return_ID:
                    # Executing Create_sale_ return function
                    try:
                        json_data = json.dumps(data.get("serials"))
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT create_sale_return(%s,%s)",[data.get('party_name'),json_data])
                        return JsonResponse({"success": True, "message": "Sale Return Sucessfull"}) 
                    except Exception as e:
                        return JsonResponse({"success": False, "message": f"Unable to Sale Return, Try Again!"}) 
                else:
                    # Executing update_sale_ return function
                    try:
                        json_data = json.dumps(data.get("serials"))
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT update_sale_return(%s,%s)",[sale_return_ID,json_data])
                        return JsonResponse({"success": True, "message": "Sale-Return Updated Sucessfully"}) 
                    except Exception as e:
                        return JsonResponse({"success": False, "message": f"Unable to Update Sale-Return, Try Again!"})
            except:
                return JsonResponse({"success": False, "message": f"Invalid Sale-Return Data!"})

        # Delete Sale Return
        if action == "delete":
            if not sale_return_ID:
                return JsonResponse({ "success": False, "message":"Navigate to Return Invoice first" })
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT delete_sale_return(%s)",[sale_return_ID])
                    return JsonResponse({"success": True, "message": "Deleted Successfully"})
            except Exception:
                return JsonResponse({"success": False, "message": "Unable to delete this Sale-Return! Try Again.."})


    return render(request,'sale_return_templates/sale_return_template.html')


def sale_return_lookup(request,serial:str):

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
            if exists[0]:
                return JsonResponse({ "success": False, "message":f"The Serial '{serial}' already exists in stock!" })
            
            cursor.execute("SELECT item_name,sold_price FROM get_serial_number_details(%s)",[serial])
            item = cursor.fetchall()
    except Exception as e:
        return JsonResponse({ "success": False, "message":f"The Serial '{serial}' is Invalid!" })
    
    return JsonResponse({ "success": True, "item_name": item[0][0], "item_price": item[0][1]})
    
def get_sale_return(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        if action == "previous":
            
            if not current_id:
                
                # getting and  previous sale return ID
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT get_last_sales_return_id()")
                        last_sale_return = cursor.fetchone()
                        
                        if not last_sale_return or not last_sale_return[0]:
                            return JsonResponse({"success": False, "message": "No Last Sale-Return!"})
                        
                        try:
                            last_sale_return = last_sale_return[0]
    
                            current_id = int(last_sale_return) + 1
                        except:
                            return JsonResponse({"success": False, "message": "Invalid Last Sale-Return data!"})
                except:
                    return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Sale-Return!"})
    
            # Validating Current sale-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid Previous Sale-Return ID!"})
            
            # Fetching Previous Sale-return data from DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_previous_sales_return(%s)",[current_id])
                    result_data = cursor.fetchone()
                 
                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Previous Sale-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Previous Sale-Return!"})
        elif action == "next":
            # Validating Current sale-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Next Sale-Return Found"})
            
            # Fetching Next sale-return data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_next_sales_return(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Next Sale-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Sale-Return!"})
            
        elif action == "current": # If no action is provided means we have to fetch current sale-return ID
            print("Entered in current----")
            # Validating Current sale-return ID
            try:
                current_id = int(current_id)
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "No Sale-Return Found"})
            
            # Fetching Next sale-return data from DB
            try:

                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_current_sales_return(%s)",[current_id])
                    result_data = cursor.fetchone()

                if not result_data or not result_data[0]:
                    return JsonResponse({"success": False, "message": "No Sale-Return Found"})
            except:
                return JsonResponse({"success": False, "message": "Data base Connection Error While getting Next Sale-Return!"})
        else:
            pass
    except:
        return JsonResponse({"success": False, "message": "Data base Error!"})
    
    # Sending to frontend
    try:
        print(result_data[0])
        return JsonResponse(result_data[0],safe=False)
    except Exception:
        return JsonResponse({"success": False, "message": "Invalid sale-return data format."})
    


def get_sale_return_summary(request):
    try:
        from_date_str = request.GET.get("from")
        to_date_str = request.GET.get("to")

        # if user want sale summary in specific dates
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
                    cursor.execute("SELECT get_sales_return_summary(%s, %s)",[from_date,to_date])
                    result = cursor.fetchone()
                
                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Sale-Return Invoices found in the given date range!"})
            except:
                return JsonResponse({"success": False, "message": "Unable fetch Sale-Return Invoices, Check your Internet Connection!"})
        # if no date is specified then fetch last 20 sale invoice summary
        else:

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT get_sales_return_summary()")
                    result = cursor.fetchone()

                if not result or not result[0]:
                    return JsonResponse({"success": False, "message": "No Sale-Return Invoices found"})
            except Exception as e:
                print(e)
                return JsonResponse({"success": False, "message": "Unable fetch Sale-Return Invoices, Check your Internet Connection!"})
        
        # now sending to frontend

        try:
            return JsonResponse(result[0], safe=False)
        except Exception as e:
            print(e)
            return JsonResponse({"success": False, "message": "Unexpected Error Occured, Please Try again!"})
        

    except Exception:
        return JsonResponse({"success": False, "message": "Invalid sale-return data format."})
