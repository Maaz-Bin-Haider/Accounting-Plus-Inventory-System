from django.shortcuts import render,redirect
from django.db import connection,DatabaseError
from django.contrib import messages
from datetime import datetime, date
from django.http import JsonResponse
import json
from psycopg2.extras import Json
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def make_receipt(request):
    if request.method == 'POST':
        action = request.POST.get("action")
        receipt_id = request.POST.get("current_id")
        if action == "submit":
            receipt_date_str = request.POST.get('receipt_date')
            party_name = request.POST.get('search_name')
            amount_str = request.POST.get('amount')
            description = request.POST.get('description')


            data = {
                "party_name":party_name.upper(),
                "amount": amount_str,
                "method": "Cash",
                "description": description if description else '',
                "receipt_date": receipt_date_str
            }

            # If party name is Empty
            if not party_name:
                messages.error(request,"Please Enter a party Name!")
                return render(request,"receipts_templates/receipt.html",data)

            # Validating Amount
            try:
                amount = float(amount_str)
                if amount <= 0:
                    messages.error(request,"Amount must be greater than Zero.")
                    return render(request,"receipts_templates/receipt.html",data)
            except:
                messages.error(request,"Invalid amount. Please enter a valid number.")
                return render(request,"receipts_templates/receipt.html",data)

            # Validate payment_date (must be in correct date format)
            try:
                # Adjust format according to your input (e.g. "YYYY-MM-DD")
                receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d").date()

                # Future Date Restriction
                if receipt_date > date.today():
                    messages.error(request, "Receipt date cannot be in the future.")
                    return render(request,"receipts_templates/receipt.html",data)

                # Making Date again Str
                receipt_date = receipt_date.strftime("%Y-%m-%d")

            except (ValueError, TypeError):
                messages.error(request,"Invalid date. Please enter a valid date in YYYY-MM-DD format.")
                return render(request,"receipts_templates/receipt.html",data)

            
            # validating party_name and Inserting Data
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[party_name.upper()])
                exists = cursor.fetchone()
                if exists:
                    data = {
                            "party_name":party_name.upper(),
                            "amount": amount,
                            "method": "Cash",
                            "description": description if description else '',
                            "receipt_date": receipt_date
                        }
                    json_data = json.dumps(data)
                    # print(json_data)
                    if not receipt_id: # Means new receipt
                        try:
                            cursor.execute("SELECT make_receipt(%s)",[json_data])
                            messages.success(request, f"Transaction completed: {amount} received from {party_name}.")
                            return redirect("receipts:receipt")
                        except Exception as e:
                            messages.error(request,f"An Unexpected Error occured Please Try Again! {e}")
                    else:   # Means we have to update receipt 
                        try:
                            cursor.execute("SELECT update_receipt(%s,%s)",[receipt_id,json_data])
                            messages.success(request, f"Transaction Updated: {amount} received from {party_name}.")
                            return redirect("receipts:receipt")
                        except Exception as e:
                            messages.error(request,f"An Unexpected Error occured Please Try Again! {e}")
                else:
                    messages.error(request,f"No such Party exists with name '{party_name}'!")
                    return render(request,"receipts_templates/receipt.html",data)
        if action == "delete":
            # print("Delete is Clicked")
            if not receipt_id:
                messages.error(request,"Navigate to Receipt first which you want to delete")
                return render(request,"receipts_templates/receipt.html")
            try:
                receipt_id = int(receipt_id)
            except:
                messages.error(request,"Navigate to Receipt first which you want to delete")
                return render(request,"receipts_templates/receipt.html")
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT delete_receipt(%s)",[receipt_id])
                    messages.success(request,"Receipt delete Sucessfully.")
                    return redirect("receipts:receipt")
            except Exception:
                messages.error(request,"Unable to delete this Receipt! Try Again..")
                return render(request,"receipts_templates/receipt.html")
            
    return render(request,"receipts_templates/receipt.html")

# if action is previous it call previous function from DB,
#  if next then same and if no action is provided it call receipt_details() which fetches current receipt using ID.
@login_required
def get_receipt(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        with connection.cursor() as cursor:
            if action == "previous":
                if not current_id:
                    print("Enter")
                    cursor.execute("SELECT get_last_receipt()")
                    last_receipt = cursor.fetchone()
                    if not last_receipt or not last_receipt[0]:
                        return JsonResponse({"error": "No Receipts found."}, status=404)
                    
                    try:
                        last_receipt = json.loads(last_receipt[0])
                        current_id = int(last_receipt['receipt_id']) + 1
                    except Exception:
                        return JsonResponse({"error":"Invalid last Receipt data"},status=500)

                try:
                    current_id = int(current_id)
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid current_id."}, status=400)
                

                cursor.execute("SELECT get_previous_receipt(%s)", [current_id])
                result = cursor.fetchone()

                if not result or not result[0]:
                    # print('-----',result)
                    return JsonResponse({
                        "error": "No previous receipt found.",
                        "info": "You are already at the first Receipt."
                    }, status=404)
                
            elif action == "next":
                try:
                    current_id = int(current_id)
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid current_id."}, status=400)

                cursor.execute("SELECT get_next_receipt(%s)", [current_id])
                result = cursor.fetchone()

                if not result or not result[0]:
                    # print('-----',result)
                    return JsonResponse({
                        "error": "No next receipt found.",
                        "info": "You are already at the latest receipt."
                    }, status=404)
            else: # No action is provided means we have to fetch receipt with current ID
                try:
                    current_id = int(current_id)
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid current_id."}, status=400)

                cursor.execute("SELECT get_receipt_details(%s)", [current_id])
                result = cursor.fetchone()

                if not result or not result[0]:
                    # print('-----',result)
                    return JsonResponse({
                        "error": "No receipt found.",
                        "info": "Can't Find this receipt may be some Internet issue!."
                    }, status=404)
    except DatabaseError:
         return JsonResponse({"error": "Database error."}, status=500)


    try:
        return JsonResponse(json.loads(result[0]))
    except Exception:
        return JsonResponse({"error": "Invalid receipt data format."}, status=500)


@login_required
def get_old_receipts(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_last_20_receipts_json(%s)", [Json({})])
            data = cursor.fetchone()

        if not data or not data[0]:
            return JsonResponse(
                {"error": "No receipt data found."}, 
                status=404
            )

        try:
            data = json.loads(data[0])
        except (json.JSONDecodeError, TypeError):
            return JsonResponse(
                {"error": "Failed to parse receipt data."}, 
                status=500
            )

        return JsonResponse(data, safe=False)

    except DatabaseError as e:
        return JsonResponse(
            {"error": "Database error occurred.", "details": str(e)}, 
            status=500
        )
    except Exception as e:
        return JsonResponse(
            {"error": "An unexpected error occurred.", "details": str(e)}, 
            status=500
        )

@login_required 
def get_receipts_date_wise(request):
    try:
        from_date_str = request.GET.get("from")
        to_date_str = request.GET.get("to")

        if not from_date_str or not to_date_str:
            return JsonResponse({"error": "Missing date range"}, status=400)
        
        # Validating Dates (must be in correct date format)
        try:
            # Adjust format according to your input (e.g. "YYYY-MM-DD")
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

            # Future Date Restriction
            if from_date > date.today() or to_date > date.today():
                return JsonResponse({"error": "Dates can't be in Future"}, status=400)

            # Making Date again Str
            from_date = from_date.strftime("%Y-%m-%d")
            to_date = to_date.strftime("%Y-%m-%d")

        except (ValueError, TypeError):
            JsonResponse({"error": "Invalid date. Please enter a valid date in YYYY-MM-DD format."}, status=400)
        
        dates = {
            "start_date": from_date,
            "end_date": to_date
        }

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT get_receipts_by_date_json(%s)",
                [json.dumps(dates)]
            )
            data = cursor.fetchone()

        if not data or not data[0]:
            return JsonResponse([], safe=False)
        
        try:
            data = json.loads(data[0])
        except (json.JSONDecodeError, TypeError):
            return JsonResponse(
                {"error": "Failed to parse receipt data."}, 
                status=500
            )

        return JsonResponse(data, safe=False)

    except Exception as e:
        print(e)
        return JsonResponse({"error": str(e)}, status=500)
    


