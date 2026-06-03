import requests
from django.shortcuts import render
from concurrent.futures import ThreadPoolExecutor

SESSION = requests.Session()  # Gjenbruker samme session for bedre ytelse og håndtering av cookies



def _hent_omsetning_fra_brreg(orgnr):
    url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
    try:
        response = SESSION.get(url, timeout=10)
        if response.status_code == 200:
            regnskaper = response.json()
            if regnskaper and len(regnskaper) > 0:
                # Riktig toppnøkkel er "resultatregnskapResultat", og omsetningen
                # ligger nøstet under driftsresultat -> driftsinntekter.
                res = regnskaper[0].get("resultatregnskapResultat", {})
                drift = res.get("driftsresultat", {}).get("driftsinntekter", {})

                # Sum driftsinntekter er det vi vil ha for eiendom (leieinntekter).
                # Faller tilbake på salgsinntekter, og til slutt finansinntekt
                # (relevant for rene holding-/investeringsselskap).
                omsetning = drift.get("sumDriftsinntekter", 0) or drift.get("salgsinntekter", 0)
                if not omsetning:
                    omsetning = res.get("finansresultat", {}).get("finansinntekt", {}).get("sumFinansinntekter", 0)

                # Årstallet utledes fra regnskapsperiode.tilDato ("2023-12-31" -> "2023")
                år = regnskaper[0].get("regnskapsperiode", {}).get("tilDato", "")[:4]
                return {"omsetning": int(omsetning), "år": år or "Ukjent"}
        return {"omsetning": 0, "år": "Ingen tall"}
    except:
        return {"omsetning": 0, "år": "Timeout/Feil"}

def hent_daglig_leder(orgnr):
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
        ((k["kommunenummer"], k["kommunenavnNorsk"]) for k in data),
        key = lambda kv: kv[1],
    ))

def potential_customers(selskapsform="AS", kommuner = None, minste_omsetning=10_000_000):
    
   
    if kommuner is None:
        kommuner = [
            "0301",
            "3201", "3203", "3205", "3207", "3209", "3212",
            "3214", "3216", "3218", "3220", "3222", "3224",
            "3226", "3228", "3230", "3232", "3234", "3236",
            "3238", "3240", "3242",
        ]
    url = "https://data.brreg.no/enhetsregisteret/api/enheter"
    
    
    
    params = {
        "organisasjonsform": selskapsform,
        "naeringskode": "68.120",   
        "kommunenummer": ",".join(kommuner),
        "size": 100,
        "konkurs": False, 
        "underAvvikling": False,    
        "underTvangsavviklingEllerTvangsopplosning": False,    
    }
        
    alle_rå_enheter = []
    gjeldende_side = 0
    total_sider = 1

    while gjeldende_side < total_sider:
        params["page"] = gjeldende_side
        try:
            response = SESSION.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Brreg feilet: {e}")
            return []
        
        total_sider = data.get("page",{}).get("totalPages", 1)
        alle_rå_enheter.extend(data.get("_embedded", {}).get("enheter", []))
        gjeldende_side += 1

    interressante_kunder = []
    MINSTE_OMSETNING = minste_omsetning

    total_enheter = len(alle_rå_enheter)

    for i, bedrift in enumerate(alle_rå_enheter, 1):
            adresse = bedrift.get("forretningsadresse", {})
            
            if adresse.get('kommunenummer') not in kommuner:
                continue    
            orgnr = bedrift.get("organisasjonsnummer")
            gateadresse = ", ".join(adresse.get("adresse", []))
            navn = bedrift.get("navn", "Ukjent")
            
            print(f"[{i}/{total_enheter}] Sjekker: {navn}...", end="", flush=True)

            regnskapsdata = _hent_omsetning_fra_brreg(orgnr)
            omsetning = regnskapsdata["omsetning"]
            årstall = regnskapsdata["år"]
            
            if omsetning == 0:
                continue

            if omsetning >= MINSTE_OMSETNING:
                lat,lon = _koordinater(adresse)
                
                print(f" -> MATCH! ({omsetning:,} kr)")
                leder_navn = hent_daglig_leder(orgnr)

                interressante_kunder.append({
                    'navn': navn,
                    'orgnr': orgnr,
                    'kommune': adresse.get('kommune', 'Ukjent'),
                    'hjemmeside': bedrift.get('hjemmeside', 'Ingen nettside oppgitt'),
                    'omsetning': f"{omsetning:,} kr",
                    'adresse': f"{gateadresse}, {adresse.get('postnummer', '')} {adresse.get('poststed', '')}".strip(", "),
                    'aar': årstall,
                    'leder': leder_navn,
                    'lat': lat,
                    'lon': lon,
                })
            else:
                print(f" -> For lav/0 kr ({omsetning:,} kr)")
    return interressante_kunder



