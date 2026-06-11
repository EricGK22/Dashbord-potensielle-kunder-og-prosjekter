from .filter import _er_relevant
from .stedsFinner import _gnr_bnr
import requests


SESSION = requests.Session()
INNSYN_URL = "https://asker-bygg.innsynsportal.no/graphql"
ASKER_ID = "d3aab42c-a204-438d-8e99-5189ae2ff468"

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


def _hent_byggesaker_asker(sok="regulering", fra_dato="2026-01-01", limit=50):
    oppslag, offset = [],0
    
    while True:
        variabler = {
            "journalDocumentsWhere": {"listId": ASKER_ID},
            "journalProceedingWhere": {},
            "journalsLimit": limit,
            "journalsOffset": offset,
            "journalsOrderBy": "journalDate_DESC",
            "journalsWhere": {
                "listId": ASKER_ID,
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
            if not _er_relevant(n.get("title", "")):
                continue
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
                "lenke": f"https://asker-bygg.innsynsportal.no/postjournal-v2/{ASKER_ID}",
            })
        if eldre:
            break
        offset += limit
    return oppslag
  
asker_KILDER = _hent_byggesaker_asker