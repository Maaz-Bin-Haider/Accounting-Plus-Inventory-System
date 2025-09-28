from django.shortcuts import render

# Create your views here.

def purchasing(request):
    return render(request,"purchase_templates/purchasing_template.html")