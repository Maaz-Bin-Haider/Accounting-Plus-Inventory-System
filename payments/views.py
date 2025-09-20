from django.shortcuts import render
from django.db import connection,DatabaseError
from django.contrib import messages
from datetime import datetime, date
from django.http import JsonResponse
import json

# Create your views here.
def make_payment(request):
    if request.method == 'POST':
        action = request.POST.get("action")
        payment_id = request.POST.get("current_id")
        if action == "submit":
            payment_date_str = request.POST.get('payment_date')
            party_name = request.POST.get('search_name')
            amount_str = request.POST.get('amount')
            description = request.POST.get('description')

            data = {
                "party_name":party_name.upper(),
                "amount": amount_str,
                "method": "Cash",
                "description": description if description else '',
                "payment_date": payment_date_str
            }


            # Validating Amount
            try:
                amount = float(amount_str)
                if amount <= 0:
                    messages.error(request,"Amount must be greater than Zero.")
                    return render(request,"payments_templates/payment.html",data)
            except:
                messages.error(request,"Invalid amount. Please enter a valid number.")
                return render(request,"payments_templates/payment.html",data)

            # Validate payment_date (must be in correct date format)
            try:
                # Adjust format according to your input (e.g. "YYYY-MM-DD")
                payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()

                # Future Date Restriction
                if payment_date > date.today():
                    messages.error(request, "Payment date cannot be in the future.")
                    return render(request,"payments_templates/payment.html",data)

                # Making Date again Str
                payment_date = payment_date.strftime("%Y-%m-%d")

            except (ValueError, TypeError):
                messages.error(request,"Invalid date. Please enter a valid date in YYYY-MM-DD format.")
                return render(request,"payments_templates/payment.html",data)

            
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
                            "payment_date": payment_date
                        }
                    json_data = json.dumps(data)
                    print(json_data)
                    if not payment_id: # Means new payment
                        try:
                            cursor.execute("SELECT make_payment(%s)",[json_data])
                            messages.success(request, f"Transaction completed: {amount} paid to {party_name}.")
                        except Exception as e:
                            messages.error(request,f"An Unexpected Error occured Please Try Again! {e}")
                    else:   # Means we have to update payment 
                        try:
                            cursor.execute("SELECT update_payment(%s,%s)",[payment_id,json_data])
                            messages.success(request, f"Transaction Updated: {amount} paid to {party_name}.")
                        except Exception as e:
                            messages.error(request,f"An Unexpected Error occured Please Try Again! {e}")
                else:
                    messages.error(request,f"No such Party exists with name '{party_name}'!")
                    return render(request,"payments_templates/payment.html",data)
        if action == "delete":
            print("Delete is Clicked")
            if not payment_id:
                messages.error(request,"Navigate to Payment first which you want to delete")
                return render(request,"payments_templates/payment.html")
            try:
                payment_id = int(payment_id)
            except:
                messages.error(request,"Navigate to Payment first which you want to delete")
                return render(request,"payments_templates/payment.html")
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT delete_payment(%s)",[payment_id])
                    messages.success(request,"Payment delete Sucessfully.")
                    return render(request,"payments_templates/payment.html")
            except Exception:
                messages.error(request,"Unable to delete this Payment! Try Again..")
                return render(request,"payments_templates/payment.html")
            


    return render(request,"payments_templates/payment.html")


def get_payment(request):
    action = request.GET.get("action")
    current_id = request.GET.get("current_id")
    try:
        with connection.cursor() as cursor:
            if action == "previous":
                if not current_id:
                    cursor.execute("SELECT get_last_payment()")
                    last_payment = cursor.fetchone()
                    if not last_payment or not last_payment[0]:
                        return JsonResponse({"error": "No payments found."}, status=404)
                    
                    try:
                        last_payment = json.loads(last_payment[0])
                        current_id = int(last_payment['payment_id']) + 1
                    except Exception:
                        return JsonResponse({"error":"Invalid last payment data"},status=500)

                try:
                        current_id = int(current_id)
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid current_id."}, status=400)
                

                cursor.execute("SELECT get_previous_payment(%s)", [current_id])
                result = cursor.fetchone()

                if not result or not result[0]:
                    print('-----',result)
                    return JsonResponse({
                        "error": "No previous payment found.",
                        "info": "You are already at the first payment."
                    }, status=404)
                
            elif action == "next":
                try:
                        current_id = int(current_id)
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid current_id."}, status=400)

                cursor.execute("SELECT get_next_payment(%s)", [current_id])
                result = cursor.fetchone()

                if not result or not result[0]:
                    print('-----',result)
                    return JsonResponse({
                        "error": "No next payment found.",
                        "info": "You are already at the latest payment."
                    }, status=404)
            else:
                return JsonResponse({"error": "Invalid action"}, status=400)
    except DatabaseError:
         return JsonResponse({"error": "Database error."}, status=500)


    try:
        return JsonResponse(json.loads(result[0]))
    except Exception:
        return JsonResponse({"error": "Invalid payment data format."}, status=500)


# TODO: Add logic to update when previous and next payment
        # Add exception handling in above task