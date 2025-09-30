from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
import json

# Create your views here.

def purchasing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # validation example
            if not data.get("party_name"):
                return JsonResponse({"success": False, "message": "Party name is required."})
            
            if data.get("party_name") != 'ff':
                return JsonResponse({"success": False, "message": "Party name is required."})

            return JsonResponse({"success": True, "message": "Data loaded successfully"})
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid request data!"})

    return render(request, "purchase_templates/purchasing_template.html")