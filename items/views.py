from django.shortcuts import render
from django.db import connection,IntegrityError
from django.contrib import messages
import json

# Create your views here.

def create_new_item(request):
    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        sale_price = request.POST.get('sale_price')
        storage = request.POST.get('storage')
        item_code = request.POST.get('item_code')
        category = request.POST.get('category')
        brand = request.POST.get('brand')

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Items WHERE item_name = UPPER(%s)",[item_name.upper()])
            exists = cursor.fetchone()

            if exists:
                messages.error(request, f"Item with the name '{item_name}' already exists!")
                return render(request, "items_templates/add_new_item.html")
            
            # Adding new Item
            items_data = {
                "item_name": item_name.upper(),
                "storage": storage,
                "sale_price": float(sale_price),
                "item_code": item_code,
                "category": category,
                "brand": brand
            }

            json_data = json.dumps(items_data)

            try:
                cursor.execute("SELECT add_item_from_json(%s)",[json_data])
                messages.success(request, f"Item '{item_name}' Added successfully!")
            except IntegrityError:
                messages.error(request, f"Item '{item_name}' already exists!")
                
        return render(request, "items_templates/add_new_item.html")

    return render(request, "items_templates/add_new_item.html")
