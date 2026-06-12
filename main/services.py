from datetime import date
import time
import requests
import os
import base64
import json
from main.models import Eiendomsverdi
import fitz

# --------------------------------------Fast funksjonalitet--------------------------------------------------

DL_URL = "https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{orgnr}/{aar}"
SESSION = requests.Session()  
BEHOLD_SIDER = 5
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OCR_MODELL = "claude-haiku-4-5-20251001"
PDF_MAPPE = "data/pdfs"

CACHE_FIL = os.path.join("data", "eiendomsverdier.json")


_PROMPT = (
    'Bildene er sider fra et norsk årsregnskap. Finn balansen og svar KUN med JSON, '
    'ingen annen tekst: {"tomter_bygninger": <tall>, "sum_varige_driftsmidler": <tall>} {Annen }'
    'med verdiene for inneværende år (venstre tallkolonne). '
    'Posten kan hete "Tomter, bygninger og annen fast eiendom" eller lignende. '
    'Bruk null hvis posten ikke finnes.'
)


#------------------------------------Selskapsinfo funksjoner---------------------------------


def _finn_enheter(selskapsform = "AS", kommuner = None, naeringskode = "68.120"):
    
    if not kommuner:
        return []
    url = "https://data.brreg.no/enhetsregisteret/api/enheter"
    params = {
        "organisasjonsform": selskapsform,
        "naeringskode": naeringskode,
        "kommunenummer": ",".join(kommuner),
        "size": 100,
        "konkurs": False,
        "underAvvikling": False,    
        "underTvangsavviklingEllerTvangsopplosning": False,    
    }
    
    enheter, side, total_sider = [],0,1
    
    while side< total_sider:
        params["page"] = side
        try:
            r = SESSION.get(url, params=params, timeout = 10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print("Brreeg søket feilet")
            break
        total_sider = data.get("page", {}).get("totalPages",1)
        enheter.extend(data.get("_embedded", {}).get("enheter", []))
        side += 1
    return[e for e in enheter if e.get("forretningsadresse", {}).get("kommunenummer") in kommuner]


def _hent_siste_regnskapsaar(orgnr):
        url = url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"
        try:
            r = SESSION.get(url, timeout= 10)
            r.raise_for_status()
            return r.json().get("sisteInnsendteAarsregnskap")
        except Exception:
            return None

def _hent_daglig_leder(orgnr):
    url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller"
    try:
        response = SESSION.get(url, timeout=10)
        if response.status_code == 200:
            for gruppe in response.json().get("rollegrupper", []):
                for rolle in gruppe.get("roller", []):
                    if rolle.get("type", {}).get("kode") == "DAGL":
                        n = rolle.get("person", {}).get("navn", {})
                        return f"{n.get('fornavn', '')} {n.get('etternavn', '')}".strip()
        return "Ikke oppført"
    except:
        return "Ukjent"
    

#------------------------------------------------------Økonomi funksjoner---------------------------------------------

def les_eiendomsverdi_cache():
    return {
        f"{r.orgnr}-{r.aar}": {
            "orgnr": r.orgnr,
            "aar": r.aar,
            "tomter_bygninger": r.tomter_bygninger,
            "sum_varige_driftsmidler": r.sum_varige_driftsmidler,
            "hentet": r.hentet.isoformat(),
        }
        for r in Eiendomsverdi.objects.all()
    }



def _last_ned_trimmet(orgnr,aar):
    os.makedirs(PDF_MAPPE, exist_ok=True)
    sti = os.path.join(PDF_MAPPE, f"{orgnr}-{aar}.pdf")
    
    if os.path.exists(sti):
        return sti

    r = SESSION.get(DL_URL.format(orgnr=orgnr, aar=aar), timeout =30)
    r.raise_for_status()
    doc = fitz.open(stream=r.content,filetype = "pdf")
    if doc.page_count > BEHOLD_SIDER:
        doc.select(list(range(BEHOLD_SIDER)))
    doc.save(sti, garbage=4, deflate = True)
    doc.close()
    return sti

def _side_velger(pdf_sti,sider = (2,3)):
    doc = fitz.open(pdf_sti)
    bilder = []   
    for i in sider:
        if i < doc.page_count:
            bilder.append(base64.b64encode(doc[i].get_pixmap(dpi=150).tobytes("png")).decode())
    doc.close()
    return bilder
    
    
def _hent_eiendoms_verdi(orgnr,aar,kun_cache=False):
    
    if not aar:
        return None
    rad = Eiendomsverdi.objects.filter(orgnr=orgnr, aar=str(aar)).first()
    if rad:
        return rad.tomter_bygninger
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Feil eller ikke satt ANTHROPIC KEY")
        return None
    try:
        sti = _last_ned_trimmet(orgnr,aar)
        bilder = _side_velger(sti)
        if not bilder:
            return None
        
        innhold = [{"type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b}} for b in bilder]
        innhold.append({"type": "text", "text": _PROMPT})


        for forsok in range(3):
            try:
                r = SESSION.post(
                    ANTHROPIC_URL,
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": OCR_MODELL, "max_tokens": 300, "messages": [{"role": "user", "content": innhold}]},
                    timeout=60,
                )
                r.raise_for_status()
                break
            except requests.exceptions.SSLError:
                if forsok == 2:
                    raise
                time.sleep(2)

        tekst = "".join(b.get("text", "") for b in r.json()["content"])
        data = json.loads(tekst.replace("```json", "").replace("```", "").strip())
        verdi = data.get("tomter_bygninger")
        total = data.get("sum_varige_driftsmidler")

        if verdi is not None and total is not None and verdi > total:
            print(f"({orgnr}: {verdi} > sum {total} - forkastet, sjekk manuelt)")
            return None

        Eiendomsverdi.objects.update_or_create(
            orgnr = orgnr, aar = str(aar),
            defaults = {"tomter_bygninger": verdi,
                        "sum_varige_driftsmidler": total}
        )
        return verdi
    except Exception as e:
        print(f"Eiendomsverdi feilet for {orgnr}: {e}")
        return None

#---------------------------------------Kart funksjoner----------------------------------------------------------
TILLATE_FYLKER = ("03", "32")

def _koordinater(adresse):
    gate = ",".join(adresse.get("adresse", []))
    sok = f"{gate} {adresse.get('postnummer','')} {adresse.get('poststed','')}".strip()
    
    if not sok:
        return None,None
    try: 
        r = SESSION.get(
            "https://ws.geonorge.no/adresser/v1/sok",
            params={"sok": sok, "treffPerSide": 1,
                    "filtrer": "adresser.representasjonspunkt"},
            timeout=10,
        )
        treff = r.json().get("adresser", [])
        if treff:
            koordinat = treff[0].get("representasjonspunkt")
            return koordinat["lat"], koordinat["lon"]
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None, None


def _kommuner():
    url = "https://api.kartverket.no/kommuneinfo/v1/kommuner"
    
    try: 
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Feil ved innhenting av kommuner: {e}")
        return {}
    return dict(sorted(
        ((k["kommunenummer"], k["kommunenavnNorsk"]) 
        for k in data 
        if k["kommunenummer"].startswith(TILLATE_FYLKER)
    ),
        key=lambda kv: kv[1]
    ))
    
def _fylker():
    url = "https://api.kartverket.no/kommuneinfo/v1/fylker"
    
    try: 
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Feil ved innhenting av fylker: {e}")
        return {}
    fylker = {}
    for f in data:
        nr = f.get("fylkesnummer")
        navn = f.get("fylkesnavn") or f.get("fylkesnavnNorsk") or nr
        if nr and nr in TILLATE_FYLKER:
            fylker[nr] = navn
    return dict(sorted(fylker.items(), key=lambda kv: kv[1]))


#---------------------------------------Kjøre funksjon---------------------------------------------------------------------

def potential_customers(selskapsform="AS", kommuner = None, _minste_eiendomsverdi=200_000_000, kun_cache = False):
    if not kommuner:
        return None
    enheter = _finn_enheter(selskapsform,kommuner)
    kunder = []
    total = len(enheter)
    
    for i, bedrift in enumerate(enheter, 1):
        adresse = bedrift.get("forretningsadresse", {})
        orgnr = bedrift.get("organisasjonsnummer")
        navn = bedrift.get("navn", "Ukjent")

        print(f"[{i}/{total}] Sjekker: {navn}...", end="", flush=True)

        aar = _hent_siste_regnskapsaar(orgnr)
        eiendomsverdi = _hent_eiendoms_verdi(orgnr, aar, kun_cache=kun_cache)

        if not eiendomsverdi:
            print(" -> ingen eiendomsverdi")
            continue
        if eiendomsverdi < _minste_eiendomsverdi:
            print(f" -> for lav ({eiendomsverdi:,} kr)")
            continue

        print(f" -> MATCH! ({eiendomsverdi:,} kr)")
        lat, lon = _koordinater(adresse)
        gateadresse = ", ".join(adresse.get("adresse", []))

        kunder.append({
            "navn": navn,
            "orgnr": orgnr,
            "kommune": adresse.get("kommune", "Ukjent"),
            "hjemmeside": bedrift.get("hjemmeside", "Ingen nettside oppgitt"),
            "eiendomsverdi": f"{eiendomsverdi:,} kr",
            "adresse": f"{gateadresse}, {adresse.get('postnummer', '')} {adresse.get('poststed', '')}".strip(", "),
            "aar": aar or "Ukjent",
            "leder": _hent_daglig_leder(orgnr),
            "lat": lat,
            "lon": lon,
        })
    return kunder
