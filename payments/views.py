from django.shortcuts import render
from django.db import connection,IntegrityError
from django.contrib import messages
import json

# Create your views here.
def make_payment(request):
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')
        party_name = request.POST.get('search_name')
        amount = request.POST.get('amount')
        description = request.POST.get('description')

        # validating party_name
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[party_name.upper()])
            exists = cursor.fetchone()
            if exists:
                pass
            else:
                messages.error(request,f"No such Party exists with name '{party_name}'!")
                return render(request,"payments_templates/payment.html")
        
        # TODO: Validate date and amount and send to DB
        print('------------',party_name)

    return render(request,"payments_templates/payment.html")