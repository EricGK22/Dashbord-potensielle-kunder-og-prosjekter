from django.core.management.base import BaseCommand

from main.models import Selskap
from main.services import (
    _finn_enheter, _hent_siste_regnskapsaar, _hent_eiendoms_verdi,
    _koordinater, _hent_daglig_leder,
)

KOMMUNER = {
    "0301": "Oslo",
    "3201": "Bærum",
    "3203": "Asker",
}

MINSTE_EIENDOMSVERDI = 10_000_000


class Command(BaseCommand):
    help = "Henter selskaper for Oslo/Asker/Bærum og lagrer dem i Selskap-tabellen."

    def add_arguments(self, parser):
        parser.add_argument("--selskapsform", default="AS")
        parser.add_argument("--minste", type=int, default=MINSTE_EIENDOMSVERDI)

    def handle(self, *args, **opts):
        selskapsform = opts["selskapsform"]
        minste = opts["minste"]

        enheter = _finn_enheter(selskapsform, list(KOMMUNER.keys()))
        total = len(enheter)
        self.stdout.write(f"Fant {total} enheter. Behandler...")

        lagret = 0
        for i, bedrift in enumerate(enheter, 1):
            adresse = bedrift.get("forretningsadresse", {})
            orgnr = bedrift.get("organisasjonsnummer")
            navn = bedrift.get("navn", "Ukjent")
            if not orgnr:
                continue

            aar = _hent_siste_regnskapsaar(orgnr)

            eiendomsverdi = _hent_eiendoms_verdi(orgnr, aar, kun_cache=True)

            if not eiendomsverdi or eiendomsverdi < minste:
                continue

            lat, lon = _koordinater(adresse)
            gateadresse = ", ".join(adresse.get("adresse", []))
            full_adresse = f"{gateadresse}, {adresse.get('postnummer', '')} {adresse.get('poststed', '')}".strip(", ")

            Selskap.objects.update_or_create(
                orgnr=orgnr,
                defaults={
                    "navn": navn,
                    "kommune": adresse.get("kommune", ""),
                    "kommunenummer": adresse.get("kommunenummer", ""),
                    "adresse": full_adresse,
                    "leder": _hent_daglig_leder(orgnr) or "",
                    "hjemmeside": bedrift.get("hjemmeside", ""),
                    "aar": aar or "",
                    "lat": lat,
                    "lon": lon,
                },
            )
            lagret += 1
            if i % 25 == 0:
                self.stdout.write(f"  [{i}/{total}] lagret så langt: {lagret}")

        self.stdout.write(self.style.SUCCESS(f"Ferdig. {lagret} selskaper lagret/oppdatert."))