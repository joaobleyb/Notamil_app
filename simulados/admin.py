from django.contrib import admin

from .models import (
    ElementoQuestao,
    ItemProvaCompartilhada,
    ProvaCompartilhada,
    Questao,
    RespostaTentativa,
    Tentativa,
)


class ElementoQuestaoInline(admin.TabularInline):
    model = ElementoQuestao
    extra = 0


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "area", "ano", "resposta_correta", "idioma_estrangeiro")
    list_filter = ("area", "ano", "idioma_estrangeiro")
    search_fields = ("enunciado", "texto_apoio", "texto_apoio_1")
    inlines = [ElementoQuestaoInline]


class RespostaTentativaInline(admin.TabularInline):
    model = RespostaTentativa
    extra = 0
    raw_id_fields = ("questao",)


@admin.register(Tentativa)
class TentativaAdmin(admin.ModelAdmin):
    list_display = ("id", "criada_em", "finalizada_em", "idioma_estrangeiro")
    list_filter = ("idioma_estrangeiro",)
    inlines = [RespostaTentativaInline]


class ItemProvaCompartilhadaInline(admin.TabularInline):
    model = ItemProvaCompartilhada
    extra = 0
    raw_id_fields = ("questao",)


@admin.register(ProvaCompartilhada)
class ProvaCompartilhadaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "criada_em", "idioma_estrangeiro", "total")
    search_fields = ("codigo",)
    inlines = [ItemProvaCompartilhadaInline]
