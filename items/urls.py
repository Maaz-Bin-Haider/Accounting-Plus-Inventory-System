from django.urls import path

from .views import create_new_item,update_item_view,autocomplete_item

app_name = "items"

urlpatterns = [
    path('add-new-item/',create_new_item,name='add_new_item'),
    path('update-item/',update_item_view,name='update_item'),
    path('autocomplete-item/', autocomplete_item, name='autocomplete_item'),
]