from django.urls import path, include
from . import views   

urlpatterns = [
    path('', views.index, name='index'),
    path('api/eiendomsverdier/', views.eiendomsverdier_api, name='eiendomsverdier'),
    path('signaler/', views.signaler, name='signaler'),
    path("signaler/<str:kilde>/", views.signaler, name="signaler_kilde"),
    path("signal/<int:signal_id>/avvis/", views.toggle_avvist, name="toggle_avvist"),
    path("signal/<int:signal_id>/kommentar/", views.legg_til_kommentar, name="legg_til_kommentar"),
    path("kommentarer/", views.kommentarer, name="kommentarer"),
    path("kommentarer/alle/", views.kommentarer, {"visning": "alle"}, name="kommentarer_alle"),
    path("kommentar/<int:kommentar_id>/slett/", views.slett_kommentar, name="slett_kommentar"),
    path("kjor/oppdater/", views.kjor_oppdater, name="kjor_oppdater"),
    path("kjor/geokod/", views.kjor_geokod, name="kjor_geokod"),
]
