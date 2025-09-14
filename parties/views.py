from django.shortcuts import render
from django.db import connection
from django.contrib import messages
import json
# Create your views here.

def create_new_party(request):
    if request.method == 'POST':
        party_name = request.POST.get('party_name')
        party_type = request.POST.get('party_type')
        contact_info = request.POST.get('contact_info')
        address = request.POST.get('address')
        opening_balance = request.POST.get('opening_balance')
        balance_type = request.POST.get('balance_type')

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Parties WHERE party_name = %s",[party_name.upper()])
            exists = cursor.fetchone()

            if exists:
                messages.error(request, f'Party with the name {party_name} already exists!')
            
            # insert new party if not exists
            party_details = {
                "party_name": party_name.upper(),
                "party_type": party_type,
                "contact_info": contact_info,
                "address": address,
                "opening_balance": int(opening_balance),
                "balance_type": balance_type
            }

            json_data = json.dumps(party_details)

            cursor.execute(
                """
                SELECT add_party_from_json(%s);
                """,
                [json_data]
            )
        messages.success(request,f"Party '{party_name}' created successfully!")

        print(party_name,party_type,contact_info,address,opening_balance,balance_type)

    return render(request,"parties_templates/add_new_party.html")