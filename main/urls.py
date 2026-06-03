# main/urls.py
from django.urls import path
from . import views   

urlpatterns = [
    path('', views.dashbord_home, name='dashbord_home'),
    path('kunder/', views.index, name='index'),
]
