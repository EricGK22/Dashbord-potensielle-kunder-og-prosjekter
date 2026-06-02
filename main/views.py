from django.shortcuts import render
from .services import potential_customers

def dashbord_home(request):
    kunder = None
    if request.method == "POST":
        kunder = potential_customers()
    return render(request, 'dashbord.html', {'kunder': kunder})