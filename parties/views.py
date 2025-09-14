from django.shortcuts import render

# Create your views here.

def create_new_party(request):
    if request.method == 'POST':
        party_name = request.POST.get('party_name')
        party_type = request.POST.get('party_type')
        contact_info = request.POST.get('contact_info')
        address = request.POST.get('address')
        opening_balance = request.POST.get('opening_balance')
        balance_type = request.POST.get('balance_type')

        print(party_name,party_type,contact_info,address,opening_balance,balance_type)

    return render(request,"parties_templates/add_new_party.html")