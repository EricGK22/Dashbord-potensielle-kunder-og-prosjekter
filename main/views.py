from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .services import _kommuner, les_eiendomsverdi_cache, potential_customers, SESSION
from django.contrib.auth.decorators import login_required
import xml.etree.ElementTree as ET
from .models import ProsjektSignal, SignalStatus, Kommentar, Eiendomsverdi, Selskap
from django.core.management import call_command
import json
from django.utils import timezone




def index(request):
    selskaper = list(Selskap.objects.all())
    orgnrs = [s.orgnr for s in selskaper]
    verdi_map = {}
    
    for ev in Eiendomsverdi.objects.filter(orgnr__in=orgnrs):
        verdi = ev.tomter_bygninger or ev.sum_varige_driftsmidler
        verdi_map[(ev.orgnr, ev.aar)] = verdi
    kunder = []
    for s in selskaper:
        verdi = verdi_map.get((s.orgnr, s.aar))
        kunder.append({
            "navn": s.navn,
            "orgnr": s.orgnr,
            "kommune": s.kommune,
            "hjemmeside": s.hjemmeside or "Ingen nettside oppgitt",
            "_verdi": verdi or 0,
            "eiendomsverdi": f"{verdi:,} kr" if verdi else "Ukjent",
            "adresse": s.adresse,
            "aar": s.aar or "Ukjent",
            "leder": s.leder or "Ikke oppført",
            "lat": s.lat,
            "lon": s.lon,
        })
        kunder.sort(key=lambda k: k["_verdi"], reverse=True)

    return render(request, "index.html", {
        "kunder": kunder,
        "antall": len(kunder),
    })
    
def eiendomsverdier_api(request):
    return JsonResponse(les_eiendomsverdi_cache())


@login_required
def signaler(request, kilde=None):
    alle = (ProsjektSignal.objects.order_by("-dato").prefetch_related("kommentar"))
    if kilde:
        alle = alle.filter(kilde=kilde)
    alle = list(alle)
    
    bruker_id = request.user.id
    punkter = []
    for s in alle:
        s.er_avvist = s.avvist
        brukere = {k.bruker_id for k in s.kommentar.all()}
        s.kommentert_av_meg = bruker_id in brukere
        s.kommentert_av_andre = bool(brukere - {bruker_id})
        
        if s.lat is not None and s.lon is not None:
            try:
                punkter.append({
                    "id": s.id,
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
    signal.avvist = not signal.avvist
    if signal.avvist:
        signal.avvist_av = request.user
        signal.avvist_tid = timezone.now()
    else:
        signal.avvist_av = None
        signal.avvist_tid = None
    signal.save()
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