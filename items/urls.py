from django.urls import path

from .views import create_new_item

urlpatterns = [
    path('add-new-item/',create_new_item,name='add_new_item'),
]