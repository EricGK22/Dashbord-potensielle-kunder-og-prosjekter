import requests
import os, re, json


KOMMUNENR = {"Asker": "3203", "Bærum": "3201"}
SESSION = requests.Session()


def _gnr_bnr(n):
    props = (n.get("proceeding") or {}).get("propertyIdentifications") or []
    deler = []
    for p in props:
        gnr = p.get("propertyNr")
        bnr = p.get("useNr")
        if gnr and bnr:
            deler.append(f"{gnr}/{bnr}")
    return ", ".join(deler)


def _geokod_matrikkel(kommune, matrikkel):
    knr = KOMMUNENR.get(kommune)
    forste = (matrikkel or "").split(",")[0].strip()
    if not knr or "/" not in forste:
        return None,None
    gnr, bnr = forste.split("/")[:2]
    try:
        r = SESSION.get("https://ws.geonorge.no/adresser/v1/sok",
                        params = {"kommunenummer": knr, "gardsnummer": gnr.strip(), 
                                    "bruksnummer": bnr.strip(), "treffPerSide": 1,
                                    "filtrer": "adresser.representasjonspunkt"}, timeout = 10)
        treff = r.json().get("adresser", [])
        if treff:
            p = treff[0]["representasjonspunkt"]
            return p["lat"], p["lon"]
    except Exception:
        pass
    return None, None

def _adresse_fra_tittel(tittel):
    nokkel = os.environ.get("ANTHROPIC_API_KEY")
    if not nokkel or not tittel:
        return ""
    prompt = ("Finn den mest presise lokasjonen i denne tittelen. "
              "Gi en norsk gateadresse (gatenavn + husnummer) hvis den finnes, "
              "ellers et område-/stedsnavn (f.eks. Fornebu, Sandvika, Nansenløkka). "
              "Lokasjonen ligger i Oslo, Bærum eller Asker. "
              "Svar BARE med adressen eller stedsnavnet, eller helt tom streng hvis ingen lokasjon finnes. "
              f"Tittel: {tittel}")
    try:
        r = SESSION.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": nokkel, "anthropic-version": "2023-06-01",
                    "content_type": "application/json"},
            json ={"model": "claude-haiku-4-5-20251001", "max_tokens": 40,
                    "messages": [{"role": "user", "content": prompt}]}, timeout=20)
        r.raise_for_status()
        return (r.json()["content"][0]["text"] or "").strip()
    except Exception as e:
        print("adresse-feil:", e)
        return ""


def _geokod_adresse(adresse, kommunenummer=None):
    if not adresse:
        return None, None
    forsok = [adresse]
    gate = re.split(r"\s+\d", adresse)[0].strip()
    if gate and gate!= adresse:
        forsok.append(gate)
    for term in forsok:
        params = {"sok": term, "treffPerSide": 1, "filtrer": "adresser.representasjonspunkt"}
        if kommunenummer:
            params["kommunenummer"] = kommunenummer
        try:
            r = SESSION.get("https://ws.geonorge.no/adresser/v1/sok", params=params, timeout=10)
            treff = r.json().get("adresser", [])
            if treff:
                p = treff[0]["representasjonspunkt"]
                return p["lat"], p["lon"]
        except Exception:
            pass
    return None, None

def _geokod_sted(navn, kommunenummer=None):
    if not navn:
        return None, None
    params = {"sok": navn, "utkoordsys": 4258, "treffPerSide": 10}
    if kommunenummer:
        params["knr"] = kommunenummer
    try:
        r = SESSION.get("https://ws.geonorge.no/stedsnavn/v1/navn", params=params, timeout=10)
        for n in r.json().get("navn", []):
            p = n.get("representasjonspunkt") or {}
            lat = p.get("nord") or p.get("lat")
            lon = p.get("øst") or p.get("ost") or p.get("lon")
            if lat and lon and 59.3 < lat < 60.7 and 10.0 < lon < 12.0:
                return lat, lon
    except Exception:
        pass
    return None, None