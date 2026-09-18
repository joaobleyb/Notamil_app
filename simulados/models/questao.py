"""Model da questão e dos elementos que compõem o corpo dela."""
from django.db import models
from django.templatetags.static import static


class Questao(models.Model):
    """Questão do ENEM com enunciado, textos de apoio e as cinco alternativas."""

    AREA_LINGUAGENS = "Linguagens"
    AREA_HUMANAS = "Humanas"
    AREA_NATUREZA = "Natureza"
    AREA_MATEMATICA = "Matemática"

    AREAS = [
        (AREA_LINGUAGENS, "Linguagens, Códigos e suas Tecnologias"),
        (AREA_HUMANAS, "Ciências Humanas e suas Tecnologias"),
        (AREA_NATUREZA, "Ciências da Natureza e suas Tecnologias"),
        (AREA_MATEMATICA, "Matemática e suas Tecnologias"),
    ]

    IDIOMA_INGLES = "ingles"
    IDIOMA_ESPANHOL = "espanhol"
    IDIOMAS = [(IDIOMA_INGLES, "Inglês"), (IDIOMA_ESPANHOL, "Espanhol")]

    ALTERNATIVAS = ["A", "B", "C", "D", "E"]

    area = models.CharField("área", max_length=20, choices=AREAS, db_index=True)
    ano = models.PositiveIntegerField("ano")
    numero = models.PositiveIntegerField("número na prova")
    enunciado = models.TextField("enunciado")
    imagem = models.TextField("imagens", blank=True, default="")
    texto_apoio = models.TextField("texto de apoio", blank=True, default="")
    fonte = models.TextField("fonte", blank=True, default="")
    idioma_estrangeiro = models.CharField(
        "idioma estrangeiro", max_length=10, choices=IDIOMAS, blank=True, default="", db_index=True
    )

    texto_apoio_1 = models.TextField(blank=True, default="")
    texto_apoio_2 = models.TextField(blank=True, default="")
    texto_apoio_3 = models.TextField(blank=True, default="")
    texto_apoio_4 = models.TextField(blank=True, default="")
    referencia_texto_1 = models.TextField(blank=True, default="")
    referencia_texto_2 = models.TextField(blank=True, default="")
    referencia_texto_3 = models.TextField(blank=True, default="")
    referencia_texto_4 = models.TextField(blank=True, default="")

    alternativa_a = models.TextField()
    alternativa_b = models.TextField()
    alternativa_c = models.TextField()
    alternativa_d = models.TextField()
    alternativa_e = models.TextField()
    resposta_correta = models.CharField(max_length=1)

    class Meta:
        verbose_name = "questão"
        verbose_name_plural = "questões"
        ordering = ["area", "ano", "numero"]
        constraints = [
            # O idioma entra na chave porque as questões de Inglês e Espanhol
            # reaproveitam o mesmo número de prova no banco original.
            models.UniqueConstraint(
                fields=["area", "ano", "numero", "idioma_estrangeiro"],
                name="questao_unica_por_area_ano_numero_idioma",
            )
        ]

    def __str__(self):
        return f"Questão {self.numero} - {self.area} - ENEM {self.ano}"

    # ------------------------------------------------------------------ #
    # Helpers de apresentação
    # ------------------------------------------------------------------ #
    @property
    def origem(self):
        """Texto de origem exibido no cabeçalho da questão."""
        return f"Questão {self.numero} - Caderno azul - ENEM {self.ano}"

    @property
    def imagens(self):
        """Lista de nomes de imagem (campo persistido separado por `|`)."""
        return [nome for nome in self.imagem.split("|") if nome]

    @property
    def alternativas(self):
        """Lista de tuplas (letra, texto) das cinco alternativas."""
        return [
            ("A", self.alternativa_a),
            ("B", self.alternativa_b),
            ("C", self.alternativa_c),
            ("D", self.alternativa_d),
            ("E", self.alternativa_e),
        ]

    def _textos_apoio_legado(self):
        """Textos de apoio no formato antigo (campo único + numerados)."""
        textos = []
        if self.texto_apoio:
            textos.append(self.texto_apoio)
            if self.fonte:
                textos.append(f"Fonte: {self.fonte}")
        pares = [
            (self.texto_apoio_1, self.referencia_texto_1),
            (self.texto_apoio_2, self.referencia_texto_2),
            (self.texto_apoio_3, self.referencia_texto_3),
            (self.texto_apoio_4, self.referencia_texto_4),
        ]
        for texto, referencia in pares:
            if texto:
                textos.append(texto)
                if referencia:
                    textos.append(referencia)
        return textos

    @staticmethod
    def _e_referencia(texto):
        return (
            texto.startswith("Fonte:")
            or "Disponível em:" in texto
            or "Acesso em:" in texto
        )

    @staticmethod
    def _elemento(tipo, conteudo):
        """Elemento pronto para o template (imagens já com a URL estática)."""
        elemento = {"tipo": tipo, "conteudo": conteudo}
        if tipo == ElementoQuestao.IMAGEM:
            elemento["url"] = static(f"simulados/img/questoes/{conteudo}.png")
        return elemento

    def corpo(self):
        """Elementos do corpo da questão, na ordem original da prova.

        Reproduz a renderização do `SimuladoActivity`: usa os elementos
        ordenados quando existirem e, caso contrário, monta a sequência do
        modo legado (textos de apoio -> imagens -> fonte).
        """
        elementos = []
        exibiu_referencia = False

        ordenados = list(self.elementos.all())
        if ordenados:
            for elemento in ordenados:
                if elemento.tipo == ElementoQuestao.ENUNCIADO:
                    continue
                if elemento.tipo == ElementoQuestao.REFERENCIA:
                    exibiu_referencia = True
                elementos.append(self._elemento(elemento.tipo, elemento.conteudo))
        else:
            for texto in self._textos_apoio_legado():
                if self._e_referencia(texto):
                    elementos.append(self._elemento(ElementoQuestao.REFERENCIA, texto))
                    exibiu_referencia = True
                else:
                    elementos.append(self._elemento(ElementoQuestao.TEXTO_APOIO, texto))
            for nome in self.imagens:
                elementos.append(self._elemento(ElementoQuestao.IMAGEM, nome))

        # Fallback: nenhuma referência explícita, mas existe fonte definida
        if not exibiu_referencia and self.fonte:
            elementos.append(self._elemento(ElementoQuestao.REFERENCIA, self.fonte))

        return elementos


class ElementoQuestao(models.Model):
    """Elemento do corpo da questão, preservando a ordem visual da prova."""

    TEXTO_APOIO = "TEXTO_APOIO"
    IMAGEM = "IMAGEM"
    REFERENCIA = "REFERENCIA"
    ENUNCIADO = "ENUNCIADO"

    TIPOS = [
        (TEXTO_APOIO, "Texto de apoio"),
        (IMAGEM, "Imagem"),
        (REFERENCIA, "Referência"),
        (ENUNCIADO, "Enunciado"),
    ]

    questao = models.ForeignKey(
        Questao, on_delete=models.CASCADE, related_name="elementos", verbose_name="questão"
    )
    ordem = models.PositiveIntegerField("ordem", default=0)
    tipo = models.CharField("tipo", max_length=20, choices=TIPOS)
    conteudo = models.TextField("conteúdo")

    class Meta:
        verbose_name = "elemento da questão"
        verbose_name_plural = "elementos da questão"
        ordering = ["questao_id", "ordem"]

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.ordem}"
