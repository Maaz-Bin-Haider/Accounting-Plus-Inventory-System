from django.shortcuts import render
from django.db import connection,IntegrityError
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
            cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s",[party_name.upper()])
            exists = cursor.fetchone()

            if exists:
                messages.error(request, f"Party with the name '{party_name}' already exists!")
                return render(request, "parties_templates/add_new_party.html")
            
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

            try:
                cursor.execute("SELECT add_party_from_json(%s);", [json_data])
                messages.success(request, f"Party '{party_name}' created successfully!")
            except IntegrityError:
                messages.error(request, f"Party '{party_name}' already exists!")

        return render(request, "parties_templates/add_new_party.html")

    return render(request,"parties_templates/add_new_party.html")


# TODO: made search view for party , if found sync all details to an html form
#       made an update view for party to update party details