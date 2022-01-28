from django.contrib import admin
from .models import *

modeli = [Tvit, Tviteras]

admin.site.register(modeli)
