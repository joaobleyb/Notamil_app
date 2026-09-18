"""Testes das regras de geração e correção do simulado."""
from django.test import TestCase
from django.urls import reverse

from .models import Questao
from .services import (
    buscar_prova_por_codigo,
    criar_prova_compartilhada,
    criar_tentativa,
    iniciar_prova_da_turma,
    salvar_resposta,
    sortear_questoes,
)


def criar_questao(**kwargs):
    dados = {
        "area": Questao.AREA_MATEMATICA,
        "ano": 2024,
        "numero": 1,
        "enunciado": "Enunciado de teste",
        "alternativa_a": "A",
        "alternativa_b": "B",
        "alternativa_c": "C",
        "alternativa_d": "D",
        "alternativa_e": "E",
        "resposta_correta": "C",
    }
    dados.update(kwargs)
    return Questao.objects.create(**dados)


class SorteioTests(TestCase):
    def test_sorteia_apenas_a_quantidade_pedida(self):
        for numero in range(1, 6):
            criar_questao(numero=numero)
        questoes = sortear_questoes(0, 0, 0, 3, Questao.IDIOMA_INGLES)
        self.assertEqual(len(questoes), 3)

    def test_filtra_idioma_estrangeiro(self):
        criar_questao(area=Questao.AREA_LINGUAGENS, numero=10, idioma_estrangeiro="ingles")
        criar_questao(area=Questao.AREA_LINGUAGENS, numero=11, idioma_estrangeiro="espanhol")
        questoes = sortear_questoes(5, 0, 0, 0, Questao.IDIOMA_ESPANHOL)
        self.assertEqual([q.numero for q in questoes], [11])


class CorrecaoTests(TestCase):
    def test_conta_acertos(self):
        questao = criar_questao()
        tentativa = criar_tentativa([questao], Questao.IDIOMA_INGLES)
        salvar_resposta(tentativa, 1, "C")
        self.assertEqual(tentativa.acertos, 1)
        self.assertEqual(tentativa.percentual, 100)

    def test_resposta_invalida_e_ignorada(self):
        questao = criar_questao()
        tentativa = criar_tentativa([questao], Questao.IDIOMA_INGLES)
        self.assertIsNone(salvar_resposta(tentativa, 1, "X"))
        self.assertEqual(tentativa.acertos, 0)


class FluxoTests(TestCase):
    def test_menu_responde(self):
        self.assertEqual(self.client.get(reverse("simulados:menu")).status_code, 200)

    def test_gerar_prova_sem_questoes_mostra_erro(self):
        resposta = self.client.post(
            reverse("simulados:gerar_prova"), {"quantidade_matematica": 2}
        )
        self.assertEqual(resposta.status_code, 200)


class CodigoTurmaTests(TestCase):
    def setUp(self):
        self.questoes = [criar_questao(numero=numero) for numero in range(1, 4)]

    def test_sem_embaralhar_todos_recebem_a_mesma_ordem(self):
        prova = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        ordens = {
            tuple(r.questao_id for r in iniciar_prova_da_turma(prova).respostas.order_by("ordem"))
            for _ in range(5)
        }
        self.assertEqual(len(ordens), 1)

    def test_embaralhar_mantem_as_questoes_e_varia_a_ordem(self):
        prova = criar_prova_compartilhada(
            self.questoes, Questao.IDIOMA_INGLES, embaralhar=True
        )
        esperado = sorted(q.id for q in self.questoes)
        ordens = set()
        for _ in range(20):
            ids = [r.questao_id for r in iniciar_prova_da_turma(prova).respostas.order_by("ordem")]
            self.assertEqual(sorted(ids), esperado)
            ordens.add(tuple(ids))
        self.assertGreater(len(ordens), 1)

    def test_codigo_gerado_e_unico_e_guarda_a_ordem(self):
        prova = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        outra = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        self.assertNotEqual(prova.codigo, outra.codigo)
        self.assertEqual(prova.total, 3)
        self.assertEqual(
            [q.numero for q in prova.questoes_ordenadas()],
            [q.numero for q in self.questoes],
        )

    def test_entrar_com_codigo_cria_tentativa_com_a_mesma_prova(self):
        prova = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        resposta = self.client.post(
            reverse("simulados:entrar_com_codigo"), {"codigo": prova.codigo.lower()}
        )
        self.assertEqual(resposta.status_code, 302)

        tentativa = prova.tentativas.get()
        self.assertEqual(
            [r.questao.numero for r in tentativa.respostas.all()],
            [q.numero for q in prova.questoes_ordenadas()],
        )

    def test_codigo_inexistente_mostra_erro(self):
        resposta = self.client.post(
            reverse("simulados:entrar_com_codigo"), {"codigo": "ZZZZZZ"}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Código não encontrado")

    def test_gerar_prova_com_codigo_redireciona_para_a_tela_do_codigo(self):
        resposta = self.client.post(
            reverse("simulados:gerar_prova"),
            {"quantidade_matematica": 2, "gerar_codigo_turma": "1"},
        )
        prova = buscar_prova_por_codigo(resposta.headers["Location"].split("/")[2])
        self.assertIsNotNone(prova)
        self.assertEqual(prova.total, 2)

    def test_tentativa_registra_a_prova_da_turma(self):
        prova = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        tentativa = iniciar_prova_da_turma(prova)
        self.assertEqual(tentativa.prova_compartilhada, prova)
