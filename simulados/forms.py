"""Formulários das telas de simulado."""
from django import forms

from .models import ProvaCompartilhada, Questao
from .services import buscar_prova_por_codigo


class GerarProvaForm(forms.Form):
    """Quantidade de questões por área + idioma estrangeiro do simulado."""

    # Teto do que uma única prova pode pedir. Sem isso, um POST com
    # quantidade_matematica=10**9 vira um SELECT gigante no banco.
    MAX_POR_AREA = 90
    MAX_TOTAL = 180

    CAMPOS_POR_AREA = {
        Questao.AREA_LINGUAGENS: "quantidade_linguagens",
        Questao.AREA_HUMANAS: "quantidade_humanas",
        Questao.AREA_NATUREZA: "quantidade_natureza",
        Questao.AREA_MATEMATICA: "quantidade_matematica",
    }

    quantidade_linguagens = forms.IntegerField(min_value=0, initial=0, required=False)
    quantidade_humanas = forms.IntegerField(min_value=0, initial=0, required=False)
    quantidade_natureza = forms.IntegerField(min_value=0, initial=0, required=False)
    quantidade_matematica = forms.IntegerField(min_value=0, initial=0, required=False)
    idioma_estrangeiro = forms.ChoiceField(
        choices=Questao.IDIOMAS, initial=Questao.IDIOMA_INGLES, required=False
    )
    gerar_codigo_turma = forms.BooleanField(required=False, initial=False)
    embaralhar_questoes = forms.BooleanField(required=False, initial=False)

    def clean_idioma_estrangeiro(self):
        return self.cleaned_data.get("idioma_estrangeiro") or Questao.IDIOMA_INGLES

    def _quantidade(self, campo):
        return self.cleaned_data.get(campo) or 0

    def clean(self):
        dados = super().clean()
        for campo in self.CAMPOS_POR_AREA.values():
            dados[campo] = self._quantidade(campo)

        quantidades = [dados[campo] for campo in self.CAMPOS_POR_AREA.values()]
        if sum(quantidades) == 0:
            raise forms.ValidationError("Selecione pelo menos uma questão.")
        if max(quantidades) > self.MAX_POR_AREA:
            raise forms.ValidationError(
                f"No máximo {self.MAX_POR_AREA} questões por área."
            )
        if sum(quantidades) > self.MAX_TOTAL:
            raise forms.ValidationError(
                f"No máximo {self.MAX_TOTAL} questões por prova."
            )
        return dados

    @property
    def total(self):
        return sum(self._quantidade(campo) for campo in self.CAMPOS_POR_AREA.values())


class EntrarComCodigoForm(forms.Form):
    """Entrada na prova compartilhada pelo código da turma."""

    codigo = forms.CharField(
        label="Código da turma",
        max_length=ProvaCompartilhada._meta.get_field("codigo").max_length,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg text-uppercase campo-codigo",
                "placeholder": "Ex.: K4XQ7B",
                "autocomplete": "off",
                "maxlength": ProvaCompartilhada._meta.get_field("codigo").max_length,
            }
        ),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        self.prova = buscar_prova_por_codigo(codigo)
        if self.prova is None:
            raise forms.ValidationError("Código não encontrado. Confira com quem criou a prova.")
        return codigo
