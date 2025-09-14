from django.urls import path

from .views import create_new_item,update_item_view

urlpatterns = [
    path('add-new-item/',create_new_item,name='add_new_item'),
    path('update-item/',update_item_view,name='update_item')
]