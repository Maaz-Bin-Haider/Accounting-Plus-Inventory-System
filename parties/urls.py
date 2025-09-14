from django.urls import path

from .views import create_new_party

urlpatterns = [
    path('add-new-party/',create_new_party,name='add_new_party'),
]