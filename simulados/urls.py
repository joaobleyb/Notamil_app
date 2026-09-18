"""Rotas do app de simulados."""
from django.urls import path

from . import views

app_name = "simulados"

urlpatterns = [
    path("", views.menu_inicial, name="menu"),
    path("gerar-prova/", views.gerar_prova, name="gerar_prova"),
    path("simulado/<uuid:tentativa_id>/<int:ordem>/", views.simulado, name="simulado"),
    path("resultado/<uuid:tentativa_id>/", views.resultado, name="resultado"),
    path("analisar/<uuid:tentativa_id>/<int:ordem>/", views.analisar_tentativa, name="analisar"),
    path("turma/<str:codigo>/", views.prova_da_turma, name="prova_da_turma"),
    path("redacao/", views.redacao, name="redacao"),
    path("entrar-com-codigo/", views.entrar_com_codigo, name="entrar_com_codigo"),
]
