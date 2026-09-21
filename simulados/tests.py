"""Testes das regras de geração e correção do simulado."""
from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import GerarProvaForm
from .views import MENSAGEM_NAO_FINALIZADA
from .models import ProvaCompartilhada, Questao, RespostaTentativa, Tentativa
from .services import (
    buscar_prova_por_codigo,
    criar_prova_compartilhada,
    criar_tentativa,
    iniciar_prova_da_turma,
    limpar_tentativas_antigas,
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


class ProtecaoTests(TestCase):
    """Barreiras contra script rodando em laço no /gerar-prova/."""

    def setUp(self):
        cache.clear()
        for numero in range(1, 11):
            criar_questao(numero=numero)

    def _gerar(self, **extra):
        dados = {"quantidade_matematica": 3}
        dados.update(extra)
        return self.client.post(reverse("simulados:gerar_prova"), dados, follow=True)

    def test_fluxo_normal_continua_funcionando(self):
        resposta = self._gerar()
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Enunciado de teste")

    def test_quantidade_acima_do_teto_nao_toca_no_banco(self):
        resposta = self._gerar(quantidade_matematica=10 ** 9)
        self.assertEqual(Tentativa.objects.count(), 0)
        self.assertContains(resposta, f"No máximo {GerarProvaForm.MAX_POR_AREA}")

    def test_total_acima_do_teto_e_recusado(self):
        por_area = GerarProvaForm.MAX_POR_AREA
        resposta = self._gerar(
            quantidade_matematica=por_area,
            quantidade_linguagens=por_area,
            quantidade_humanas=por_area,
        )
        self.assertEqual(Tentativa.objects.count(), 0)
        self.assertContains(resposta, f"No máximo {GerarProvaForm.MAX_TOTAL}")

    def test_limite_por_ip_interrompe_a_criacao(self):
        for _ in range(25):
            self._gerar(quantidade_matematica=1)
        self.assertEqual(Tentativa.objects.count(), 20)

    def test_tentativa_de_outra_sessao_da_404(self):
        self._gerar()
        tentativa_id = Tentativa.objects.get().id
        outra_sessao = self.client_class()
        for rota, args in (
            ("simulados:simulado", [tentativa_id, 1]),
            ("simulados:analisar", [tentativa_id, 1]),
            ("simulados:resultado", [tentativa_id]),
        ):
            self.assertEqual(outra_sessao.get(reverse(rota, args=args)).status_code, 404)


class GabaritoTests(TestCase):
    """A correção só abre depois de finalizar a prova."""

    def setUp(self):
        cache.clear()
        for numero in range(1, 6):
            criar_questao(numero=numero)
        self.client.post(
            reverse("simulados:gerar_prova"), {"quantidade_matematica": 3}
        )
        self.tentativa = Tentativa.objects.get()

    def test_correcao_antes_de_finalizar_volta_para_a_prova(self):
        for rota, args in (
            ("simulados:analisar", [self.tentativa.id, 1]),
            ("simulados:resultado", [self.tentativa.id]),
        ):
            resposta = self.client.get(reverse(rota, args=args))
            self.assertRedirects(
                resposta,
                reverse("simulados:simulado", args=[self.tentativa.id, 1]),
            )

    def test_gabarito_nao_vaza_no_corpo_da_resposta(self):
        resposta = self.client.get(
            reverse("simulados:analisar", args=[self.tentativa.id, 1]), follow=True
        )
        self.assertContains(resposta, MENSAGEM_NAO_FINALIZADA)

    def test_depois_de_finalizar_a_correcao_abre(self):
        self.tentativa.finalizada_em = timezone.now()
        self.tentativa.save()
        for rota, args in (
            ("simulados:analisar", [self.tentativa.id, 1]),
            ("simulados:resultado", [self.tentativa.id]),
        ):
            self.assertEqual(
                self.client.get(reverse(rota, args=args)).status_code, 200
            )

    def test_finalizar_pelo_fluxo_normal_leva_ao_resultado(self):
        resposta = self.client.post(
            reverse("simulados:simulado", args=[self.tentativa.id, 3]),
            {"alternativa": "C", "acao": "finalizar"},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, MENSAGEM_NAO_FINALIZADA)


class LimpezaTests(TestCase):
    """Faxina das tentativas antigas."""

    def setUp(self):
        self.questoes = [criar_questao(numero=numero) for numero in range(1, 4)]

    def _envelhecer(self, obj, dias):
        type(obj).objects.filter(pk=obj.pk).update(
            criada_em=timezone.now() - timedelta(days=dias)
        )

    def test_remove_abandonadas_e_preserva_o_resto(self):
        velha = criar_tentativa(self.questoes, Questao.IDIOMA_INGLES)
        recente = criar_tentativa(self.questoes, Questao.IDIOMA_INGLES)
        finalizada = criar_tentativa(self.questoes, Questao.IDIOMA_INGLES)
        finalizada.finalizada_em = timezone.now()
        finalizada.save()
        self._envelhecer(velha, 40)
        self._envelhecer(finalizada, 40)

        self.assertEqual(limpar_tentativas_antigas(dias=30), (1, 0))
        self.assertEqual(
            set(Tentativa.objects.values_list("pk", flat=True)),
            {recente.pk, finalizada.pk},
        )
        self.assertEqual(RespostaTentativa.objects.filter(tentativa=velha).count(), 0)

    def test_provas_de_turma_respondidas_sao_preservadas(self):
        usada = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        vazia = criar_prova_compartilhada(self.questoes, Questao.IDIOMA_INGLES)
        criar_tentativa(self.questoes, Questao.IDIOMA_INGLES, prova_compartilhada=usada)
        self._envelhecer(usada, 40)
        self._envelhecer(vazia, 40)

        self.assertEqual(limpar_tentativas_antigas(dias=30, incluir_provas=True)[1], 1)
        self.assertEqual(
            list(ProvaCompartilhada.objects.values_list("pk", flat=True)), [usada.pk]
        )

    def test_comando_de_limpeza_roda(self):
        call_command("limpar_tentativas", "--dias", "1", verbosity=0)
