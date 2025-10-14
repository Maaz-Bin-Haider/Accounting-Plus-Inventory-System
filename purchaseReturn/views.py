from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

# Create your views here.

def createPurchaseReturn(request):
    return render(request,'purchase_return_templates/purchase_return_template.html')


def purchase_return_lookup(request,serial:str):

    #validating Serial Number
    try:
        serial = str(serial)
    except:
        return JsonResponse({ "success": False, "message":"Invalid Serial Number" })
    
    # checking in Current Stock
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT in_stock FROM get_serial_number_details(%s)",[serial])
            exists = cursor.fetchone()
            if not exists[0]:
                return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
            
            cursor.execute("SELECT item_name FROM get_serial_number_details(%s)",[serial])
            item_name = cursor.fetchone()
    except Exception as e:
        return JsonResponse({ "success": False, "message":f"The Serial '{serial}' does not exists in stock!" })
    
    return JsonResponse({ "success": True, "item_name": item_name[0] })
    