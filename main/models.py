from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Selskap(models.Model):
    orgnr          = models.CharField(max_length=9, unique=True, db_index=True)
    navn           = models.CharField(max_length=255)
    kommune        = models.CharField(max_length=100, blank=True)
    kommunenummer  = models.CharField(max_length=4, blank=True, db_index=True)
    adresse        = models.CharField(max_length=255, blank=True)
    leder          = models.CharField(max_length=255, blank=True)
    hjemmeside     = models.CharField(max_length=255, blank=True)
    aar            = models.CharField(max_length=4, blank=True)
    lat            = models.FloatField(null=True, blank=True)
    lon            = models.FloatField(null=True, blank=True)
    oppdatert      = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.navn} ({self.orgnr})"

class Eiendomsverdi(models.Model):
    orgnr = models.CharField(max_length=9,db_index=True)
    aar = models.CharField(max_length=4)
    tomter_bygninger = models.BigIntegerField(null=True,blank=True)
    sum_varige_driftsmidler = models.BigIntegerField(null=True,blank=True)
    hentet = models.DateField(auto_now=True)
    
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["orgnr", "aar"], name="unik_orgnr_aar"),
        ]
    
    def __str__(self):
        return f"{self.orgnr} ({self.aar}): {self.tomter_bygninger}"
    
    
class ProsjektSignal(models.Model):
    kilde = models.CharField(max_length=50)
    kommune = models.CharField(max_length=50)
    type = models.CharField(max_length=80)
    referanse = models.CharField(max_length=200)
    tittel = models.CharField(max_length=500)
    status = models.CharField(max_length=100, blank=True)
    dato = models.DateField(null=True, blank=True)
    lenke = models.URLField(max_length=300, blank=True)
    oppdaget = models.DateField(auto_now_add=True)
    part = models.CharField(max_length=800, blank=True)
    matrikkel = models.CharField(blank=True)
    lat = models.FloatField(null = True, blank=True)
    lon = models.FloatField(null=True,blank=True)
    frist = models.DateField(null=True, blank=True)
    avvist = models.BooleanField(default = False)
    avvist_av = models.ForeignKey(User, null = True, blank = True, on_delete= models.SET_NULL, related_name ="avviste_signaler")
    avvist_tid = models.DateTimeField(null =True, blank = True)

    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kilde","referanse"],
                                    name = "unik_kilde_referanse")
        ]
        verbose_name_plural = "Prosjektsignaler"
    def __str__(self):
        return f"{self.kommune}: {self.tittel}"
    
    
class Kommentar(models.Model):
    signal = models.ForeignKey(ProsjektSignal, on_delete=models.CASCADE, related_name="kommentar")
    bruker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tekst = models.TextField()
    opprettet = models.DateTimeField(auto_now_add = True)
    
    
    def __str__(self):
        return f"{self.bruker}: {self.tekst[:40]}"
    
class SignalStatus(models.Model):
    bruker = models.ForeignKey(User, on_delete=models.CASCADE)
    signal = models.ForeignKey(ProsjektSignal, on_delete=models.CASCADE)
    avvist = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("bruker", "signal")