"""
URL configuration for financee project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from parties import urls as parties_urls
from items import urls as items_urls
from payments import urls as payments_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('parties/', include(parties_urls,namespace='parties')),
    path('items/', include(items_urls, namespace='items')),
    path('payments/',include(payments_urls,namespace='payments')),
]
