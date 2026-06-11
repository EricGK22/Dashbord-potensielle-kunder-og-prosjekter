from django.core.management.base import BaseCommand
from main.models import ProsjektSignal
from main.scrapers.stedsFinner import (_geokod_matrikkel, _adresse_fra_tittel, _geokod_adresse, _geokod_sted)
import time

KOMMUNENR = {"Asker": "3203", "Bærum": "3201", "Oslo": "0301"}


class Command(BaseCommand):
    help = "Geokoder signaler: gnr/bnr -> adresse i tittel -> stedsnavn"

    def handle(self, *args, **options):
        rader = ProsjektSignal.objects.filter(lat__isnull=True)
        total = rader.count()
        antall = 0
        for i,s in enumerate(rader, start =1):
            lat = lon = None
            term = ""
            if s.matrikkel:                                 
                lat, lon = _geokod_matrikkel(s.kommune, s.matrikkel)

            if lat is None and s.tittel:                      
                term = _adresse_fra_tittel(s.tittel)
                knr = KOMMUNENR.get(s.kommune)
                lat, lon = _geokod_adresse(term, knr)
                if lat is None:
                    lat,lon = _geokod_sted(term, knr)

            if lat is not None and 59.3 < lat < 60.7 and 10.0 < lon < 12.0:
                s.lat, s.lon = lat, lon
                s.save()
                antall += 1
                status = f"OK ({lat:.4f}, {lon:.4f})"
            elif lat is not None:
                status = f"forkastet utenfor region ({lat:.2f}, {lon:.2f})"
            else:
                status = "ingen treff"


            print(f"[{i}/{total}] {s.kommune or '-'} | {(s.tittel or '')[:40]} | term='{term}' -> {status}", flush=True)
            time.sleep(0.2)

        self.stdout.write(f"Geokodet {antall} signaler")