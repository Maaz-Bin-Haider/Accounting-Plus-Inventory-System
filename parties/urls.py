from django.urls import path

from .views import create_new_party, update_party,auto_complete_party

urlpatterns = [
    path('add-new-party/',create_new_party,name='add_new_party'),
    path('update-party/',update_party,name='update_party'),
    path('autocomplete-party',auto_complete_party,name='autocomplete_party'),
]