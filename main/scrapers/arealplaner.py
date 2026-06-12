import requests
SESSION = requests.Session()

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
        if isinstance(data,list):
            planer = data
        else:
            planer = []
            for v in data.values():
                if isinstance(v,list):
                    planer = v
                    break
        
        for plan in planer:
            dato = (plan.get("sistBehandlet") or plan.get("iKraft") or "")[:10] or None
            tittel = plan
            if not dato or dato < fra_dato:
                continue
            plan_id = plan.get("id") or plan.get("planId")
            link = f"https://arealplaner.no/{kunde}/arealplaner/{plan_id}"
            oppslag.append({
                "kilde": "Arealplaner",
                "kommune": kommune,
                "type": plan.get("planType", "Arealplan"),
                "referanse": str(plan.get("planId") or plan_id),
                "tittel": plan.get("planNavn", ""),
                "status": plan.get("planStatus", ""),
                "dato": dato,
                "lenke": link,
            })
    return oppslag

arealplaner_KILDER = [
    lambda: _hent_arealplaner("asker3203", "Asker"),
    lambda: _hent_arealplaner("baerum3201", "Bærum"),
]