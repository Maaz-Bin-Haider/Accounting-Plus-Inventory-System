from django.shortcuts import render

# Create your views here.

def create_new_item(request):
    return render(request, "items_templates/add_new_item.html")
