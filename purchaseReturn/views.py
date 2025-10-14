from django.shortcuts import render

# Create your views here.

def createPurchaseReturn(request):
    return render(request,'purchase_return_templates/purchase_return_template.html')