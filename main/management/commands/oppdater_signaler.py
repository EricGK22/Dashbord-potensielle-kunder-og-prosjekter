from django.core.management.base import BaseCommand

from main.models import ProsjektSignal
from main.scraper import KILDER

class Command(BaseCommand):
    help = "Henter prosjektsignaler fra alle kilder i scraper.py"
    
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