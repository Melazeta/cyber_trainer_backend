import trainer.views as views

from django.urls import path
from cyber_trainer.settings import API_URL


urlpatterns = [
    path(API_URL + "stats/", views.PlayerStats.as_view()),
    path(API_URL + "cases/", views.Cases.as_view())
]