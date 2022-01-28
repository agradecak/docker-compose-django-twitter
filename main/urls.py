from django.urls import path
from .views import TvitoviList

urlpatterns = [
    path('tvitovi/', TvitoviList.as_view())
]