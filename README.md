# NotaMil

Versão web do simulador **NotaMil** (simulados no estilo ENEM), feita com
**Django + Bootstrap 5**. Mantém o mesmo fluxo do app: gerar prova → resolver →
resultado → analisar tentativa.

## Recursos

- Sorteio de questões por área (Linguagens, Humanas, Natureza, Matemática) e idioma estrangeiro.
- Código de turma: a turma inteira responde exatamente a mesma prova.
- Embaralhar por aluno (opcional): mesmas questões, ordem diferente em cada prova — evita cola.
- QR Code do código, para a turma entrar pela câmera do celular.
- Correção automática com análise questão a questão.

## Como rodar

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_questoes     # carrega as 71 questões do ENEM
python manage.py runserver
```

Acesse <http://127.0.0.1:8000/>.

Para usar o admin (`/admin/`): `python manage.py createsuperuser`.

## Estrutura

```
notamil_web/
├── manage.py
├── requirements.txt
├── notamil_web/              # projeto (settings, urls, wsgi, asgi)
└── simulados/                 # app
    ├── models/                # models em pacote
    │   ├── questao.py         # Questao + ElementoQuestao (ordem visual da prova)
    │   ├── prova_compartilhada.py  # ProvaCompartilhada + ItemProvaCompartilhada (código de turma)
    │   └── tentativa.py       # Tentativa + RespostaTentativa
    ├── services/              # regras de negócio
    │   ├── prova_service.py   # sorteio, criação da tentativa, correção
    │   └── seed_service.py    # carga do banco de questões
    ├── management/commands/seed_questoes.py
    ├── fixtures/questoes.json # 71 questões extraídas do app Android
    ├── static/simulados/      # css, js e as 21 imagens das questões
    ├── templates/simulados/
    ├── forms.py · urls.py · views.py · admin.py · tests.py
```

## Telas

| Rota | Tela | Equivalente no Android |
|---|---|---|
| `/` | Menu inicial | `MenuInicialActivity` |
| `/gerar-prova/` | Configuração do simulado | `GerarProvaActivity` |
| `/simulado/<uuid>/<n>/` | Resolução das questões | `SimuladoActivity` |
| `/resultado/<uuid>/` | Acertos e aproveitamento | `ResultadoSimuladoActivity` |
| `/analisar/<uuid>/<n>/` | Revisão com gabarito | `AnalisarTentativaActivity` |
| `/redacao/` | Redação (em desenvolvimento) | `RedacaoActivity` |
| `/turma/<codigo>/` | Código gerado para compartilhar a prova | — (novo) |
| `/entrar-com-codigo/` | Entrada na prova da turma pelo código | `EntrarComCodigoActivity` |

## Código de turma

Ao gerar uma prova, ligue a opção **Criar código**: o sorteio é congelado em uma
`ProvaCompartilhada` e o sistema devolve um código de 6 caracteres (sem `O`, `0`,
`I` e `1` para evitar confusão). Quem entrar com esse código em
`/entrar-com-codigo/` responde exatamente as mesmas questões, na mesma ordem — cada
pessoa com a sua própria tentativa. A tela do código mostra o resumo por área e
quantas pessoas já finalizaram.

## Diferenças em relação ao app Android

- **Código de turma implementado**: no app a tela existia só como interface.
- **Tentativas persistidas**: a prova sorteada vira um registro `Tentativa`, o que
  permite navegar por URL e rever o resultado depois (no app o estado se perdia).
- **Idioma estrangeiro normalizado**: o seed grava `ingles` / `espanhol`, alinhado
  com o filtro da geração da prova (no app o seed gravava `Inglês` / `Espanhol` e o
  filtro nunca casava).
- **Deduplicação por área + ano + número + idioma**: as 5 questões de Inglês e as 5
  de Espanhol usam a mesma numeração de prova; sem o idioma na chave, as de Inglês
  eram sobrescritas.
- **Elementos ordenados em tabela própria** (`ElementoQuestao`) em vez de JSON em
  coluna de texto.

## Testes

```bash
python manage.py test
```
