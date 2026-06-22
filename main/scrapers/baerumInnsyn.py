import requests
from .filter import _er_relevant
from urllib.parse import quote
from datetime import date, timedelta

SESSION = requests.Session()
BAERUM_BASE = "https://innsynpluss.onacos.no"
BAERUM_PAGE = f"{BAERUM_BASE}/baerum/postliste/"
BAERUM_INIT = f"{BAERUM_BASE}/api/presentation/v2/nye-innsyn/overviewInit"
BAERUM_SAKSTYPE = "at-8de09341__cd12__4975__9460__e28961550ab5-BS!qUGVU5"
BAERUM_OVERVIEW = f"{BAERUM_BASE}/api/presentation/v2/nye-innsyn/overview"

BAERUM_HEADERS = {
    "accept": "*/*",
    "content_type": "application/json",
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
    

def _hent_byggesaker_baerum(fra_dato=None, sok="regulering", maks_sider = 150):
    if fra_dato is None:
        fra_dato = (date.today() - timedelta(days=182)).isoformat()
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
    
    items = _hent_side(BAERUM_INIT, _body())  
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
                "lenke": f"{BAERUM_PAGE}#/?searchTerm={quote(tittel)}",
            })
        if nye == 0 or len(items) < 10:
            break         
        side += 1
        if side > maks_sider:
            break
        items = _hent_side(BAERUM_OVERVIEW, _body(page=side))
    return oppslag



baerum_KILDER = _hent_byggesaker_baerum