from django.shortcuts import render
from django.db import connection,IntegrityError
from django.contrib import messages
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required

@login_required
def create_new_item(request):
    
    
    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        sale_price = request.POST.get('sale_price')
        storage = request.POST.get('storage')
        item_code = request.POST.get('item_code')
        category = request.POST.get('category')
        brand = request.POST.get('brand')

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Items WHERE UPPER(item_name) = %s", [item_name.upper()])
            exists = cursor.fetchone()

            if exists:
                return JsonResponse({
                    "status": "error",
                    "message": f"Item with the name '{item_name}' already exists!"
                })

            # Prepare JSON data for function
            item_data = {
                "item_name": item_name.upper(),
                "storage": storage,
                "sale_price": float(sale_price or 0),
                "item_code": item_code,
                "category": category,
                "brand": brand
            }

            json_data = json.dumps(item_data)

            try:
                if request.user.groups.filter(name="view_only_users").exists():
                    return JsonResponse({
                        "status": "error",
                        "message": "You do not have permission to create items."
                    })
                cursor.execute("SELECT add_item_from_json(%s)", [json_data])
                return JsonResponse({
                    "status": "success",
                    "message": f"Item '{item_name}' added successfully!"
                })
            except IntegrityError:
                return JsonResponse({
                    "status": "error",
                    "message": f"Item '{item_name}' already exists!"
                })

    return render(request, "items_templates/add_new_item.html")




@login_required
def get_item_by_name(item_name):

    with connection.cursor() as cursor:
        cursor.execute("SELECT get_item_by_name(%s)",[item_name.upper()])
        row = cursor.fetchone()

    if row and row[0]:
        data =  json.loads(row[0])
        return data[0] if data else None

    return None


@login_required
def update_item_view(request):
    context = {}

    # Case 1: Search form submitted
    if request.method == "GET" and "search_name" in request.GET:
        search_name = request.GET.get("search_name")
        item = get_item_by_name(search_name)
        if item:
            context["item"] = item
        else:
            context["not_found"] = True
        


    if request.method == 'POST':
        item_id = request.POST.get("item_id")
        data = {
            "item_name": request.POST.get("item_name").upper(),
            "sale_price": float(request.POST.get("sale_price") or 0),
            "storage": request.POST.get("storage"),
            "item_code": request.POST.get("item_code"),
            "category": request.POST.get("category"),
            "brand": request.POST.get("brand"),
        }

        if item_id:
            data["item_id"] = int(item_id) 

        json_data = json.dumps(data)

        with connection.cursor() as cursor:
            if item_id:

                try:
                    if request.user.groups.filter(name="view_only_users").exists():
                        return JsonResponse({
                            "status": "error",
                            "message": "You do not have permission to create items."
                        })
                    cursor.execute("SELECT update_item_from_json(%s)",[json_data])
                    messages.success(request, f"Item '{data['item_name']}' Updated successfully!")
                except Exception as e:
                    messages.error(request, f"An Unexpected Error Occured! {e}")
            else: # means adding new item

                try:
                    if request.user.groups.filter(name="view_only_users").exists():
                        return JsonResponse({
                            "status": "error",
                            "message": "You do not have permission to create items."
                        })
                    cursor.execute("SELECT add_item_from_json(%s)",[json_data])
                    messages.success(request, f"Item '{data['item_name']}' Added successfully!")
                except IntegrityError:
                    messages.error(request, f"Item '{data['item_name']}' already exists!")


    return render(request, "items_templates/update_item.html",context)


@login_required
def autocomplete_item(request):
    if 'term' in request.GET:
        term = request.GET.get('term').upper()
        with connection.cursor() as cursor:
            cursor.execute("SELECT item_name FROM Items WHERE UPPER(item_name) LIKE %s LIMIT 10", [term + '%'])
            rows = cursor.fetchall()
        suggestions = [row[0] for row in rows]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)

