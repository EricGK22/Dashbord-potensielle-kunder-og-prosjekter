from django.core.management.base import BaseCommand

from main.models import ProsjektSignal
from main.scrapers.arealplaner import _hent_arealplaner
from main.scrapers.askerInnsyn import _hent_byggesaker_asker
from main.scrapers.baerumInnsyn import _hent_byggesaker_baerum
from main.scrapers.doffin import _hent_doffin


# Kommando for sletting av oppslag:
# python manage.py shell -c "from main.models import ProsjektSignal as P; from main.scrapers.filter import _er_relevant; ider=[s.id for s in P.objects.all() if not _er_relevant(s.tittel)]; n,_=P.objects.filter(id__in=ider).delete(); print('slettet', n)"


KILDER = [
    lambda: _hent_arealplaner("asker3203", "Asker"),
    lambda: _hent_arealplaner("baerum3201", "Bærum"),
    _hent_byggesaker_asker,
    _hent_byggesaker_baerum,
    _hent_doffin,
]
class Command(BaseCommand):
    help = "Henter prosjektsignaler fra alle webscraperne i scrapers-mappen"
    
    def handle(self, *args, **opt):
        nye = 0
        for kilde in KILDER:
            try:
                signaler = kilde()
            except Exception as e:
                self.stderr.write(f"{kilde.__name__} feilet: {e}")
                continue
            for s in signaler:
                _, opprettet = ProsjektSignal.objects.update_or_create(
                    kilde=s["kilde"], referanse=s["referanse"],
                    defaults={k: v for k, v in s.items() if k not in ("kilde", "referanse")},
                )
                nye += opprettet
            self.stdout.write(f"{kilde.__name__}: {len(signaler)} signaler hentet")
        self.stdout.write(self.style.SUCCESS(f"Ferdig - {nye} nye signaler lagret."))