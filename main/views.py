from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render
from .services import _fylker, _kommuner, les_eiendomsverdi_cache, potential_customers, SESSION
from main.models import Eiendomsverdi, ProsjektSignal
import xml.etree.ElementTree as ET


def index(request):
    kommuner = _kommuner()
    fylker = _fylker()
    kunder = None
    feilmelding = None
    minste_eiendomsverdi=200_000_000
    if request.method == "POST":
        valgte_kommuner = set(request.POST.getlist("kommunenummer"))
        valgte_fylker = request.POST.getlist("fylkesnummer")
        selskapsform = request.POST.get("organisasjonsform", "AS")
        
        raw = request.POST.get("minste_eiendomsverdi", "")
        raw = raw.replace(" ", "").replace("\xa0", "").replace(".", "").replace(",", "")
        
        if raw.isdigit():
            minste_eiendomsverdi = int(raw)
            print("VIEW minste_omsetning =", minste_eiendomsverdi)
        
        for fnr in valgte_fylker:
            valgte_kommuner.update(nr for nr in kommuner if nr.startswith(fnr))
        
        if not valgte_kommuner:
            feilmelding= "Du har ikke valgt noen kommuner eller fylker"
        else:
            kunder = potential_customers(selskapsform,sorted(valgte_kommuner),minste_eiendomsverdi)
        
    return render(request, "index.html",{
            "kommuner": kommuner,
            "fylker": fylker,
            "kunder": kunder,
            "feilmelding": feilmelding,
            "minste_eiendomsverdi": minste_eiendomsverdi,
        })
    
def eiendomsverdier_api(request):
    return JsonResponse(les_eiendomsverdi_cache())


def signaler(request, kilde=None):
    alle = ProsjektSignal.objects.order_by("-dato")
    if kilde:
        alle = alle.filter(kilde=kilde)
    kilder = (ProsjektSignal.objects.exclude(kilde="").values_list("kilde", flat=True).distinct().order_by("kilde"))
    return render(request, "signaler.html", {
        "signaler": alle,
        "valgt_kilde": kilde,
        "kilder": kilder,
    })
    
