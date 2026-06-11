import requests
from .filter import _er_relevant



SESSION = requests.Session()
URL = "https://api.doffin.no/webclient/api/v2/search-api/search"
LOKASJONER = ["NO084", "NO081"]
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.doffin.no",
    "referer": "https://www.doffin.no/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
}

def _hent_doffin(lokasjoner = LOKASJONER, per_side=50, maks_sider =20):
    oppslag, side =[], 1
    def hent_body(side = 1):
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
        return body
    while True:
        r = SESSION.post(URL, headers=HEADERS, json = hent_body(side), timeout = 20)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits") or []
        if not hits:
            break
        for h in hits:
            tittel = h.get("heading", "")
            if not _er_relevant(tittel):
                continue
            nid = h.get("id", "")
            oppslag.append({
                "kilde": "Doffin",
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

doffin_KILDER = _hent_doffin