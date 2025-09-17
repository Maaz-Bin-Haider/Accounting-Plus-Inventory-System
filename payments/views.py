from django.shortcuts import render

# Create your views here.
def make_payment(request):
    return render(request,"payments_templates/payment.html")