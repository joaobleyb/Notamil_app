"""Proteções contra uso abusivo: limite de requisições e posse da tentativa.

Sem login, qualquer script pode chamar `gerar-prova` em laço e encher o banco de
tentativas. Aqui ficam as duas barreiras baratas contra isso:

* `dentro_do_limite` — teto de provas criadas por IP em uma janela de tempo.
* sessão — só quem criou a tentativa consegue abri-la depois.
"""
from django.core.cache import cache

# acao -> (máximo de usos, janela em segundos)
LIMITES = {
    "gerar_prova": (20, 3600),
    "entrar_com_codigo": (40, 3600),
}

CHAVE_SESSAO = "tentativas"
# Quantas tentativas a mesma sessão continua conseguindo reabrir.
MAX_TENTATIVAS_LEMBRADAS = 50


def _identificador(request):
    """IP de origem, respeitando o proxy https da hospedagem."""
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "desconhecido"


def dentro_do_limite(request, acao):
    """Contabiliza mais um uso da ação e diz se o IP ainda está dentro do teto."""
    limite, janela = LIMITES[acao]
    chave = f"limite:{acao}:{_identificador(request)}"

    # `add` + `incr` preserva o vencimento da janela; `set` o reiniciaria a cada uso.
    cache.add(chave, 0, janela)
    try:
        usos = cache.incr(chave)
    except ValueError:  # a chave venceu entre o add e o incr
        cache.set(chave, 1, janela)
        usos = 1
    return usos <= limite


def registrar_tentativa_na_sessao(request, tentativa):
    """Marca a tentativa como pertencente a quem está navegando."""
    ids = request.session.get(CHAVE_SESSAO, [])
    ids.append(str(tentativa.id))
    request.session[CHAVE_SESSAO] = ids[-MAX_TENTATIVAS_LEMBRADAS:]
    return tentativa


def tentativa_da_sessao(request, tentativa_id):
    """A tentativa foi criada nesta sessão?"""
    return str(tentativa_id) in request.session.get(CHAVE_SESSAO, [])
