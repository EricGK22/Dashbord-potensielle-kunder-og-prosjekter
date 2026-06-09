from django.db import models

# Create your models here.

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
    tittel = models.CharField(max_length=300)
    status = models.CharField(max_length=100, blank=True)
    dato = models.DateField(null=True, blank=True)
    lenke = models.URLField(max_length=300, blank=True)
    oppdaget = models.DateField(auto_now_add=True)
    part = models.CharField(max_length=800, blank=True)
    matrikkel = models.CharField(blank=True)
    lat = models.FloatField(null = True, blank=True)
    lon = models.FloatField(null=True,blank=True)
    frist = models.DateField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kilde","referanse"],
                                    name = "unik_kilde_referanse")
        ]
        verbose_name_plural = "Prosjektsignaler"
    def __str__(self):
        return f"{self.kommune}: {self.tittel}"