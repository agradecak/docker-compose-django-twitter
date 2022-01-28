from django.views.generic import ListView
from .models import *
# Create your views here.

class TvitoviList(ListView):
    model = Tvit

