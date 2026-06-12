from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .services import _kommuner, les_eiendomsverdi_cache, potential_customers, SESSION
from django.contrib.auth.decorators import login_required
import xml.etree.ElementTree as ET
from .models import ProsjektSignal, SignalStatus, Kommentar, Eiendomsverdi
from django.core.management import call_command
import json




def index(request):
    kommuner = _kommuner()
    kunder = None
    feilmelding = None
    minste_eiendomsverdi=200_000_000
    if request.method == "POST":
        valgte_kommuner = set(request.POST.getlist("kommunenummer"))
        valgte_kommuner &= set(kommuner.keys()) 
        selskapsform = request.POST.get("organisasjonsform", "AS")
        
        raw = request.POST.get("minste_eiendomsverdi", "")
        raw = raw.replace(" ", "").replace("\xa0", "").replace(".", "").replace(",", "")
        
        if raw.isdigit():
            minste_eiendomsverdi = int(raw)
            print("VIEW minste_omsetning =", minste_eiendomsverdi)
        
        if not valgte_kommuner:
            feilmelding= "Du har ikke valgt noen kommuner eller fylker"
        else:
            kunder = potential_customers(selskapsform,sorted(valgte_kommuner),minste_eiendomsverdi)
        
    return render(request, "index.html",{
            "kommuner": kommuner,
            "kunder": kunder,
            "feilmelding": feilmelding,
            "minste_eiendomsverdi": minste_eiendomsverdi,
        })
    
def eiendomsverdier_api(request):
    return JsonResponse(les_eiendomsverdi_cache())


@login_required
def signaler(request, kilde=None):
    alle = (ProsjektSignal.objects.order_by("-dato").prefetch_related("kommentar"))
    if kilde:
        alle = alle.filter(kilde=kilde)
    alle = list(alle)
    
    avviste_ids = set(
        SignalStatus.objects.filter(bruker=request.user, avvist=True).values_list("signal_id", flat = True)
    )
    
    bruker_id = request.user.id
    punkter = []
    for s in alle:
        s.er_avvist = s.id in avviste_ids
        brukere = {k.bruker_id for k in s.kommentar.all()}
        s.kommentert_av_meg = bruker_id in brukere
        s.kommentert_av_andre = bool(brukere - {bruker_id})
        
        if s.lat is not None and s.lon is not None:
            try:
                punkter.append({
                    "lat": float(s.lat),
                    "lon": float(s.lon),
                    "tittel": s.tittel or "",
                    "part": s.part or "",
                    "lenke": s.lenke or "",
                    "kilde": s.kilde or "",
                    "avvist": s.er_avvist,
                    "kommentert": s.kommentert_av_meg or s.kommentert_av_andre,
                })
            except (TypeError, ValueError):
                pass
    
    kilder = (ProsjektSignal.objects.exclude(kilde="").values_list("kilde", flat = True).distinct().order_by("kilde"))
    
    return render(request, "signaler.html", {
        "signaler": alle,
        "valgt_kilde": kilde,
        "kilder": kilder,
        "punkter_json": json.dumps(punkter),
    })



@login_required
def toggle_avvist(request, signal_id):
    signal = get_object_or_404(ProsjektSignal, id=signal_id)
    status, _ = SignalStatus.objects.get_or_create(bruker=request.user, signal=signal)
    status.avvist = not status.avvist
    status.save()
    return redirect(request.META.get("HTTP_REFERER") or "signaler")

@login_required
def legg_til_kommentar(request, signal_id):
    if request.method == "POST":
        tekst = (request.POST.get("tekst") or "").strip()
        if tekst:
            signal = get_object_or_404(ProsjektSignal, id=signal_id)
            Kommentar.objects.create(signal = signal, bruker = request.user, tekst = tekst)
    return redirect(request.META.get("HTTP_REFERER") or "signaler")


@login_required
def kommentarer(request, visning="mine"):
    qs = (Kommentar.objects.select_related("signal", "bruker").order_by("-opprettet"))
    if visning == "mine":
        qs = qs.filter(bruker=request.user)
    return render(request, "kommentarer.html", {"kommentarer": qs, "visning": visning})

@login_required
def slett_kommentar(request, kommentar_id):
    k = get_object_or_404(Kommentar, id=kommentar_id, bruker=request.user)
    k.delete()
    return redirect(request.META.get("HTTP_REFERER" or "kommentarer"))
@login_required
def kjor_oppdater(request):
    if request.method == "POST":
        call_command("oppdater_signaler")
    return redirect(request.META.get("HTTP_REFERER") or "signaler")

@login_required
def kjor_geokod(request):
    if request.method == "POST":
        call_command("geokod_signaler")
    return redirect(request.META.get("HTTP_REFERER") or "signaler")