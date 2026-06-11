OK = (
    "boligblokk", "blokk", "leilighet", "rekkehus", "kjedehus", "flermannsbolig",
    "boligprosjekt", "boligområde", "punkthus",
    "næringsbygg", "kontorbygg", "kontor", "forretningsbygg", "forretning",
    "kjøpesenter", "handelsbygg", "hotell", "lager", "logistikk", "industribygg",
    "produksjonsbygg", "felt"
    "skole", "barnehage", "sykehjem", "omsorgsbolig", "helsehus", "institusjon",
    "idrettshall", "flerbrukshall", "svømmehall", "idrettsanlegg",
    "parkeringshus", "parkeringskjeller", "rådhus",
    "reguleringsplan", "områderegulering", "detaljregulering", "områdeplan",
    "kommunedelplan", "transformasjon", "fortetting", "hageby", "kvartal", "totalentreprise",
    "byggentreprise", "byggentrepenør"
)

FILTER = (
    "garasje", "carport", "terrasse", "veranda", "balkong", "levegg", "gjerde",
    "platting", "basseng", "anneks", "brygge","ildsted", "skilt",
    "forstøtningsmur", "rekkverk", "hekk", "fasade",
    "påbygg", "enebolig", "fritidsbolig", "hytte", "tomannsbolig",
    "varmepumpe", "vindu", "tilbygg", "loft", "sommerhus", "sekundærleilighet",
    "mikrohus", "takoppløft", "lagringsbod", "redskapshus", "sykkelgarasje",
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
    "korrespondanse", "avslag", "adressevedtak", "tømmeavtale",  "oppsumering", "fortau",
    "natursteinmur", "rørlegger", "svar", "oppsummering", "annonsebestilling", "statsforvalter", "faktura", "tilbakemelding",
    "gyldighet","sjekkliste", "supplering", "oppheving", "massedeponi", "igangsetting", "rammeavtale", "tjenester"
)


def _er_relevant(tittel):
    t = (tittel or "").lower()
    if any(ord_ in t for ord_ in HARD_FILTER): 
        return False
    if any(ord_ in t for ord_ in OK):        
        return True
    if any(ord_ in t for ord_ in FILTER):       
        return False
    return True