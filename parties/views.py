from django.shortcuts import render

# Create your views here.

def create_new_party(request):
    return render(request,"parties_templates/add_new_party.html")