from django.urls import path
from . import views   

urlpatterns = [
    path('', views.index, name='index'),
    path('api/eiendomsverdier/', views.eiendomsverdier_api, name='eiendomsverdier'),
    path('signaler/', views.signaler, name='signaler'),
    path("signaler/<str:kilde>/", views.signaler, name="signaler_kilde"),
]
