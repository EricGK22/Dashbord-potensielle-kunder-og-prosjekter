from django.shortcuts import render
from .services import _kommuner, potential_customers

def dashbord_home(request):
    kunder = None
    if request.method == "POST":
        kunder = potential_customers()
    return render(request, 'dashbord.html', {'kunder': kunder})

def index(request):
    kommuner = _kommuner()
    kunder = None
    minste_omsetning = 10000000
    if request.method == "POST":
        valgte = request.POST.getlist("kommunenummer") or None
        selskapsform = request.POST.get("organisasjonsform", "AS")
        
        raw = request.POST.get("minste_omsetning", "")
        raw = raw.replace(" ", "").replace("\xa0", "").replace(".", "").replace(",", "")
        if raw.isdigit():
            minste_omsetning = int(raw)
            print("VIEW minste_omsetning =", minste_omsetning)
        
        kunder = potential_customers(selskapsform, valgte, minste_omsetning)
        
        
    return render(request, "index.html", 
                  {"kommuner": kommuner, 
                   "kunder": kunder,
                   "minste_omsetning": minste_omsetning,
                   })