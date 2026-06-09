import requests
import json
import urllib.parse
import os
import re

SESSION = requests.Session()

# Kommando for sletting av oppslag:
# python manage.py shell -c "from main.models import ProsjektSignal as P; from main.scraper import _er_relevant; ider=[s.id for s in P.objects.filter(type='Byggesak') if not _er_relevant(s.tittel)]; n,_=P.objects.filter(id__in=ider).delete(); print('slettet', n)"

OK = (
    "boligblokk", "blokk", "leilighet", "rekkehus", "kjedehus", "flermannsbolig",
    "boligprosjekt", "boligområde", "punkthus",
    "næringsbygg", "kontorbygg", "kontor", "forretningsbygg", "forretning",
    "kjøpesenter", "handelsbygg", "hotell", "lager", "logistikk", "industribygg",
    "produksjonsbygg",
    "skole", "barnehage", "sykehjem", "omsorgsbolig", "helsehus", "institusjon",
    "idrettshall", "flerbrukshall", "svømmehall", "idrettsanlegg",
    "parkeringshus", "parkeringskjeller", "rådhus",
    "reguleringsplan", "områderegulering", "detaljregulering", "områdeplan",
    "kommunedelplan", "transformasjon", "fortetting", "hageby", "kvartal",
)

FILTER = (
    "klage", "merknad", "nabovarsel", "automatisk tilbakemelding", "dialogmøte",
    "uttalelse", "mangelbrev", "oversendelse", "purring", "foreløpig",
    "garasje", "carport", "terrasse", "veranda", "balkong", "levegg", "gjerde",
    "platting", "basseng", "anneks", "brygge", "pipe", "ildsted", "skilt",
    "støttemur", "forstøtningsmur", "rekkverk", "hekk", "fasade",
    "påbygg", "enebolig", "fritidsbolig", "hytte", "tomannsbolig",
    "solcelle", "varmepumpe", "oppmåling", "seksjon", "vindu", "tilbygg", "loft",
    "sommerhus"
)

HARD_FILTER = (
    "klage", "merknad", "nabovarsel", "automatisk tilbakemelding", "dialogmøte",
    "uttalelse", "mangelbrev", "oversendelse", "purring", "foreløpig",
    "oppmåling", "seksjon", "støyskjerm", "pipe","støttemur", "solcelle",
    "sommerhus","avsluttes", "spørsmål","henvendelse", "ferdigattest", "brukstillatelse",
    "anmodning", "orientering", "bekreftelse", "kvittering", "ettersending", "tilleggsopplysninger", "supplerende",
    "redegjørelse", "rettelse", "befaring", "forhåndskonferanse",
    "innsyn", "kopi", "referat", "protokoll", "avslut", "trukket", "trekking", "avvist", "avvisning", "avslag",
    "mangelbrev", "pålegg", "tilsyn", "forespørsel", "utgått", "falt bort", "bortfall", "ber om", "komplettering",
    "korrespondanse", "Avslag"
)


def _er_relevant(tittel):
    t = (tittel or "").lower()
    if any(ord_ in t for ord_ in HARD_FILTER):   # støy -> fjern alltid
        return False
    if any(ord_ in t for ord_ in OK):        # storprosjekt -> behold
        return True
    if any(ord_ in t for ord_ in FILTER):        # småsak -> fjern
        return False
    return True

# ----------------------Arealplaner.no----------------------------------------------

arealplanerno_WAAPI_TOKEN = "D7D7FFB4-1A4A-44EA-BD15-BCDB6CEF8CA5"

def _hent_arealplaner(kunde, kommune, fra_dato = "2026", status_ids=(1,2,3)):

    url = f"https://api.arealplaner.no/api/kunder/{kunde}/arealplaner"
    oppslag = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://arealplaner.no",
        "Referer": "https://arealplaner.no/",
        "X-WAAPI-Token": arealplanerno_WAAPI_TOKEN,
    }
    for status_id in status_ids:
        params = {"planStatusId": status_id}
        r = SESSION.get(
            url,
            params=params,
            headers=headers,
            timeout = 15,
        )
        r.raise_for_status()
        data = r.json()
        planer = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v,list)), []
        )
        
        for plan in planer:
            dato = (plan.get("sistBehandlet") or plan.get("iKraft") or "")[:10] or None
            if not dato or dato < fra_dato:
                continue
            plan_id = plan.get("id") or plan.get("planId")
            link = f"https://arealplaner.no/{kunde}/arealplaner/{plan_id}"
            oppslag.append({
                "kilde": "arealplaner.no",
                "kommune": kommune,
                "type": plan.get("planType", "Arealplan"),
                "referanse": str(plan.get("planId") or plan_id),
                "tittel": plan.get("planNavn", ""),
                "status": plan.get("planStatus", ""),
                "dato": dato,
                "lenke": link,
            })
    return oppslag


# -----------------------------innsynsportal Asker------------------------------------------
INNSYN_URL = "https://asker-bygg.innsynsportal.no/graphql"
ASKER_LISTID = "d3aab42c-a204-438d-8e99-5189ae2ff468"


KOMMUNENR = {"Asker": "3203", "Bærum": "3201"}


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

INNSYN_HEADERS = {
    "accept": "*/*",
    "accept-language": "nb,no;q=0.9,en;q=0.8",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "origin": "https://asker-bygg.innsynsportal.no",
    "referer": "https://asker-bygg.innsynsportal.no/postjournal-v2/d3aab42c-a204-438d-8e99-5189ae2ff468?params=%7B%22search%22%3A%22ramme%22%7D",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
}

_ASKER_QUERY = """query FetchMoreJournals($journalsLimit: Int!, $journalsOffset: Int, $journalsWhere: SearchJournalsWhere!, $journalProceedingWhere: JournalProceedingWhere, $journalDocumentsWhere: JournalDocumentsWhere!, $journalsOrderBy: SearchJournalsOrderBy) {
  journals: searchJournals(
    limit: $journalsLimit
    offset: $journalsOffset
    where: $journalsWhere
    proceedingWhere: $journalProceedingWhere
    orderBy: $journalsOrderBy
  ) {
    nodes {
      ...JournalResult
      __typename
    }
    __typename
  }
}

fragment JournalResult on Journal {
  id
  archiveId
  journalDate
  classified
  documentDate
  title
  sequenceNumber
  caseworkers
  senders
  unpublished
  recipients
  archiveSystem {
    id
    name
    __typename
  }
  department {
    id
    name
    __typename
  }
  status {
    id
    description
    name
    __typename
  }
  subArchive {
    id
    name
    __typename
  }
  type {
    id
    name
    description
    __typename
  }
  documents(where: $journalDocumentsWhere) {
    id
    classified
    title
    order
    type {
      id
      name
      __typename
    }
    __typename
  }
  proceeding {
    id
    sequenceNumber
    type {
      id
      name
      __typename
    }
    subArchive {
      id
      name
      __typename
    }
    propertyIdentifications {
      id
      useNr
      propertyNr
      __typename
    }
    __typename
  }
  __typename
}"""

def _gnr_bnr(n):
    props = (n.get("proceeding") or {}).get("propertyIdentifications") or []
    deler = []
    for p in props:
        gnr = p.get("propertyNr")
        bnr = p.get("useNr")
        if gnr and bnr:
            deler.append(f"{gnr}/{bnr}")
    return ", ".join(deler)


def _hent_byggesaker_asker(sok="ramme", fra_dato="2026-01-01", limit=50):
    oppslag, offset = [],0
    
    while True:
        variabler = {
            "journalDocumentsWhere": {"listId": ASKER_LISTID},
            "journalProceedingWhere": {},
            "journalsLimit": limit,
            "journalsOffset": offset,
            "journalsOrderBy": "journalDate_DESC",
            "journalsWhere": {
                "listId": ASKER_LISTID,
                "search": sok,
                "journalFromDate": None,
                "journalToDate": None,
                "departmentIdIn": None,
            },
        }
        r = SESSION.post(INNSYN_URL,headers=INNSYN_HEADERS, timeout=20,
                            json = {"operationName": "FetchMoreJournals", 
                                    "query": _ASKER_QUERY, 
                                    "variables": variabler})
        r.raise_for_status()
        nodes = ((r.json().get("data") or {}).get("journals") or {}).get("nodes") or []
        if not nodes:
            break
        eldre = False
        for n in nodes:
            dato = (n.get("journalDate") or "")[:10] or None
            if not dato or dato<fra_dato:
                eldre = True
                continue
            # if not _er_relevant(n.get("title", "")):
            #     continue
            part = (n.get("recipients") or n.get("senders") or [""])
            navn = n.get("title", "")
            oppslag.append({
                "kilde": "Asker postliste",
                "kommune": "Asker",
                "type": "Byggesak",
                "referanse": n.get("sequenceNumber", ""),
                "tittel": navn,
                "status": (n.get("status") or {}).get("name", ""),
                "dato": dato,
                "part": part[0] if part else "",
                "matrikkel": _gnr_bnr(n),
                "lenke": f"https://asker-bygg.innsynsportal.no/postjournal-v2/{ASKER_LISTID}",
            })
        if eldre:
            break
        offset += limit
    return oppslag


# ----------------------------- Bærum (ACOS Innsyn Pluss) ------------------------------

BAERUM_BASE = "https://innsynpluss.onacos.no"
BAERUM_PAGE = f"{BAERUM_BASE}/barum-gard/sok-i-plan-og-byggesaker-fra-2015/"
BAERUM_INIT = f"{BAERUM_BASE}/api/presentation/v2/nye-innsyn/overviewInit"
BAERUM_SAKSTYPE = "at-8de09341__cd12__4975__9460__e28961550ab5-RS!qUGVU5"
BAERUM_OVERVIEW = f"{BAERUM_BASE}/api/presentation/v2/nye-innsyn/overview"

BAERUM_HEADERS = {
    "accept": "*/*",
    "content_type": "application.json",
    "origin": BAERUM_BASE,
    "referer": BAERUM_PAGE,
    "devicetype": "desktop",
    "menypunktid": "1631",
    "portalid": "100",
    "sprakid": "1",
    "x-anti-csrf": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
}

def _norsk_dato(s):
    
    try:
        d,m,y = s.split(".")
        return f"{y}-{m}-{d}"
    except Exception:
        return None
    

def _hent_byggesaker_baerum(fra_dato="2026-01-01", sok="ramme", maks_sider = 150):
    oppslag = []
    s = requests.Session()
    s.get(BAERUM_PAGE, headers={"user-agent": BAERUM_HEADERS["user-agent"]}, timeout= 20)
    def _body(page = None):
        kv = [
            {"key": "Dato", "value": fra_dato},
            {"key": "Dato", "value": "Other"},
            {"key": "searchTerm", "value": sok},
        ]
        if page:
            kv.append({"key": "page", "value": str(page)})
        return {"type": 0, "keyValues": kv}
    
    def _hent_side(url, body):
        r = s.post(url, headers=BAERUM_HEADERS, json=body, timeout =20)
        r.raise_for_status()
        data = r.json()
        return (((data.get("content") or {}).get("searchItems") or  {}).get("items")) or []
    
    items = _hent_side(BAERUM_INIT, _body())   # side 1
    side = 1
    sett = set()
    while items:
        nye = 0
        for it in items:
            ident = it.get("identifier")
            if ident in sett:
                continue
            sett.add(ident)
            nye += 1
            tittel = it.get("title", "")
            if not _er_relevant(tittel):
                continue
            props = it.get("properties") or {}
            oppslag.append({
                "kilde": "Bærum postliste",
                "kommune": "Bærum",
                "type": "Byggesak",
                "referanse": props.get("dokumentID") or ident or "",
                "tittel": tittel,
                "status": {"J": "Journalført"}.get(it.get("status", ""), it.get("status", "")),
                "dato": _norsk_dato(props.get("dato", "")),
                "part": props.get("mottaker") or props.get("avsender", ""),
                "matrikkel": "",
                "lenke": BAERUM_PAGE,
            })
        if nye == 0 or len(items) < 10:
            break          # ingen nye saker = vi gjentar oss selv, eller siste side
        side += 1
        if side > maks_sider:
            break
        items = _hent_side(BAERUM_OVERVIEW, _body(page=side))
    return oppslag



# ----------------------------------Doffin.no-----------------------------------------------------------

DOFFIN_URL = "https://api.doffin.no/webclient/api/v2/search-api/search"
DOFFIN_LOKASJONER = ["NO084", "NO081"]
DOFFIN_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.doffin.no",
    "referer": "https://www.doffin.no/",
    "user-agent": BAERUM_HEADERS["user-agent"],
}

def _hent_doffin(lokasjoner = DOFFIN_LOKASJONER, per_side=50, maks_sider =20):
    oppslag, side = [], 1
    while True:
        body = {
            "numHitsPerPage": per_side,
            "page": side,
            "searchString": "",
            "sortBy": "RELEVANCE",
            "facets": {
                "cpvCodesLabel": {"checkedItems": []},
                "cpvCodesId": {"checkedItems": []},
                "type": {"checkedItems": ["COMPETITION"]},
                "status": {"checkedItems": ["ACTIVE"]},
                "contractNature": {"checkedItems": ["WORKS"]},
                "procurementStrategicLabels": {"checkedItems":[]},
                "publicationDate": {"from": None, "to": None},
                "location": {"checkedItems": lokasjoner},
                "buyer": {"checkedItems": []},
                "winner": {"checkedItems": []},
            }
        }
        r = SESSION.post(DOFFIN_URL, headers=DOFFIN_HEADERS, json = body, timeout = 20)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits") or []
        if not hits:
            break
        for h in hits:
            nid = h.get("id", "")
            oppslag.append({
                "kilde": "Doffin.no",
                "kommune": (h.get("placeOfPerformance") or [""])[0]
                            or {"NO081": "Oslo", "NO084": "Akershus"}.get((h.get("locationId") or [""])[0], "Annet"),
                "type": "Anbud",
                "referanse": nid,
                "tittel": h.get("heading", ""),
                "status": h.get("status", ""),
                "dato": (h.get("publicationDate") or "")[:10] or None,
                "part": (h.get("buyer") or [{}])[0].get("name", ""),
                "matrikkel": "",
                "frist": (h.get("deadline") or "")[:10] or None,
                "lenke": f"https://www.doffin.no/notices/{nid}",
            })
        if len(oppslag) >= (data.get("numHitsTotal") or 0):
            break
        side+=1
        if side > maks_sider:
            break
    return oppslag


# ----------------------------------------Geokoding av adresser med Claude--------------------------------------------

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
    except Exception:
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





KILDER = [lambda: _hent_arealplaner("asker3203", "Asker"),
            lambda: _hent_arealplaner("baerum3201", "Bærum"),
            _hent_byggesaker_asker,
            _hent_byggesaker_baerum,
            _hent_doffin]