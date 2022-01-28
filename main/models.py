from django.db import models
import string

class Tviteras(models.Model):
    ime = models.CharField(max_length=50)
    hendl = models.CharField(max_length=50)
    opis = models.TextField()
    lokacija = models.CharField(max_length=50)
    datum_pridruzivanja = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.hendl

class Tvit(models.Model):
    tijelo = models.TextField()
    stvorio = models.ForeignKey(Tviteras, on_delete=models.CASCADE)
    vrijeme_stvaranja = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} {}".format(self.vrijeme_stvaranja, self.stvorio)

    class Meta:
        ordering = ('-vrijeme_stvaranja',)
