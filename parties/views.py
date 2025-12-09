from django.shortcuts import render
from django.db import connection,IntegrityError
from django.contrib import messages
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required

@login_required
def create_new_party(request):
    if request.method == 'POST':
        party_name = request.POST.get('party_name')
        party_type = request.POST.get('party_type')
        contact_info = request.POST.get('contact_info')
        address = request.POST.get('address')
        opening_balance = request.POST.get('opening_balance')
        balance_type = request.POST.get('balance_type')

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Parties WHERE UPPER(party_name) = %s", [party_name.upper()])
            exists = cursor.fetchone()

            if exists:
                return JsonResponse({
                    "status": "error",
                    "message": f"Party with the name '{party_name}' already exists!"
                })

            # Insert new party
            party_details = {
                "party_name": party_name.upper(),
                "party_type": party_type,
                "contact_info": contact_info,
                "address": address,
                "opening_balance": int(opening_balance or 0),
                "balance_type": balance_type
            }

            json_data = json.dumps(party_details)

            try:
                if request.user.groups.filter(name="view_only_users").exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "You do not have permission to Add Parties."
                    })
                cursor.execute("SELECT add_party_from_json(%s);", [json_data])
                return JsonResponse({
                    "status": "success",
                    "message": f"Party '{party_name}' created successfully!"
                })
            except IntegrityError:
                return JsonResponse({
                    "status": "error",
                    "message": f"Party '{party_name}' already exists!"
                })

    return render(request, "parties_templates/add_new_party.html")

@login_required
def get_party_by_name(party_name:str):
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_party_by_name(%s)",[party_name.upper()])
        row = cursor.fetchone()
    
    if row and row[0]:
        data = json.loads(row[0])
        return data
    return None

@login_required
def auto_complete_party(request):
    if 'term' in request.GET:
        term = request.GET.get('term').upper()

        with connection.cursor() as cursor:
            cursor.execute("SELECT party_name FROM Parties WHERE UPPER(party_name) LIKE %s LIMIT 10",[term + '%'])
            rows = cursor.fetchall()
        
        suggestions = [row[0] for row in rows]
        
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)

@login_required
def update_party(request):
    context = {}
    if request.method == 'GET' and 'search_name' in request.GET:
        search_name = request.GET.get('search_name')
        party = get_party_by_name(party_name=search_name)

        if party:
            context['party'] = party
        else:
            context["not_found"] = True

        

    if request.method == 'POST':
        party_id = request.POST.get('party_id')
        data = {
            "party_name": request.POST.get('party_name').upper(),
            "party_type": request.POST.get('party_type'),
            "contact_info": request.POST.get('contact_info'),
            "address": request.POST.get('address'),
            "opening_balance": float(request.POST.get('opening_balance') or 0),
            "balance_type": request.POST.get('balance_type')
        }

        if party_id:
            data["party_id"] = int(party_id)
        
        json_data = json.dumps(data)

        with connection.cursor() as cursor:
            if party_id:
                
                try:
                    if request.user.groups.filter(name="view_only_users").exists():
                        return JsonResponse({
                            "status": "error",
                            "message": "You do not have permission to Update Parties."
                        })
                    cursor.execute("SELECT update_party_from_json(%s,%s)",[int(party_id),json_data])
                    messages.success(request,f"Updated '{data['party_name']}' Sucessfully!")
                except Exception as e:
                    messages.error(request, f"An Unexpected Error Occured! {e}")
            else:
                try:
                    if request.user.groups.filter(name="view_only_users").exists():
                        return JsonResponse({
                            "status": "error",
                            "message": "You do not have permission to Add Parties."
                        })
                    cursor.execute("SELECT add_party_from_json(%s);", [json_data])
                    messages.success(request, f"Party '{data['party_name']}' created successfully!")
                except IntegrityError:
                    messages.error(request, f"Party '{data['party_name']}' already exists!")


    return render(request,"parties_templates/update_party.html",context)


