from django.contrib import admin
from django.urls import path, include
from accounts.views import home  # This is the view function

urlpatterns = [
    path('', home, name='home'),  # This will return your HttpResponse message
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
]

