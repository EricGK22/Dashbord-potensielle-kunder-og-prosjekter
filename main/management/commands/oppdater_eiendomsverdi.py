from django.core.management.base import BaseCommand

from main.services import(
    _kommuner,
    _finn_enheter,
    _hent_eiendoms_verdi,
    _hent_siste_regnskapsaar,
)

class Command(BaseCommand):
    help = "Henter og lagrer 'Tomter, bygninger o.a. fast eiendom' for alle selskaper i valgte områder"
    
    def add_arguments(self, parser):
        parser.add_argument("--fylke", nargs = "*", default=[], help = "Fylkesnummer, f.eks. 03 32")
        parser.add_argument("--kommune", nargs = "*", default=[], help = "kommunesnummer, f.eks. 0301, 3203")
        parser.add_argument("--selskapsform", default = "AS")
        
    def handle(self, *args, **opt):
        alle_kommuner = _kommuner()
        valgte = set(opt["kommune"])
        for fnr in opt["fylke"]:
            valgte.update(nr for nr in alle_kommuner if nr.startswith(fnr))
        if not valgte:
            self.stderr.write("Ingen områder valgt. Bruk --fylke og/eller --kommune.")
            return
        
        enheter = _finn_enheter(opt["selskapsform"], sorted(valgte))
        total = len(enheter)
        self.stdout.write(f"Fant {total} selskaper i {len(valgte)} kommuner. "
                            f"(Allerede cachede er gratis og går fort.)")
        med_verdi = uten_verdi = 0
        
        for i, bedrift in enumerate(enheter, 1):
            orgnr = bedrift.get("organisasjonsnummer")
            navn = bedrift.get("navn", "ukjent")
            aar = _hent_siste_regnskapsaar(orgnr)
            verdi = _hent_eiendoms_verdi(orgnr,aar)
            if verdi is None:
                uten_verdi += 1
                self.stdout.write(f"[{i}/{total}] {navn}: -")
            else:
                med_verdi += 1
                self.stdout.write(f"[{i}/{total}] {navn}: {verdi:,} kr")
                
        self.stdout.write(self.style.SUCCESS(
            f"Ferdig: {med_verdi} med verdi, {uten_verdi} uten/feilet. "
            f"Alt ligger i data/eiendomsverdier.json (se /api/eiendomsverdier/)."
        ))
            
            