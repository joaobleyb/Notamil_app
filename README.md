# NotaMil

Simulador de provas no estilo ENEM, feito com **Django + Bootstrap 5**.
O fluxo é: gerar prova → resolver → resultado → analisar tentativa.

## Recursos

- Sorteio de questões por área (Linguagens, Humanas, Natureza, Matemática) e idioma estrangeiro.
- Código de turma: a turma inteira responde exatamente a mesma prova.
- Embaralhar por aluno (opcional): mesmas questões, ordem diferente em cada prova — evita cola.
- QR Code do código, para a turma entrar pela câmera do celular.
- Correção automática com análise questão a questão.
- Proteções contra uso abusivo: teto de questões por prova, limite por IP,
  tentativa presa à sessão e faxina das tentativas antigas.

## Como rodar

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_questoes     # carrega as 71 questões do ENEM
python manage.py runserver
```

O banco padrão é o **SQLite** do próprio Django: não precisa instalar nem ligar nada.
Para usar **MySQL** (veja [Banco de dados](#3-banco-de-dados)), defina
`DJANGO_DB_ENGINE=mysql` e as credenciais.

Acesse <http://127.0.0.1:8000/>.

Para usar o admin (`/admin/`): `python manage.py createsuperuser`.

> Em desenvolvimento, rode com `DJANGO_DEBUG=1` (no Windows: `set DJANGO_DEBUG=1`).
> Sem essa variável o projeto assume modo de produção.

## Hospedagem

O projeto já vai pronto para um host WSGI (Render, Railway, PythonAnywhere, VPS com
Nginx...). Os arquivos estáticos são servidos pelo próprio Django via WhiteNoise, então
não é preciso configurar Nginx para o CSS e as imagens.

### 1. Variáveis de ambiente

| Variável | Exemplo | Para que serve |
| --- | --- | --- |
| `DJANGO_DEBUG` | `0` | Mantenha `0` em produção (nunca `1`). |
| `DJANGO_SECRET_KEY` | *(string longa e aleatória)* | Assina sessões e CSRF. Sem ela, uma chave nova é gerada a cada reinício e o login do admin cai. |
| `DJANGO_ALLOWED_HOSTS` | `notamil.escola.br,www.notamil.escola.br` | Domínios que podem servir o site. |
| `DJANGO_CSRF_ORIGINS` | `https://notamil.escola.br` | Obrigatório em HTTPS, senão os formulários dão erro 403. |
| `DJANGO_SSL_REDIRECT` | `1` | Opcional: força http → https (deixe `0` se o proxy já redireciona). |

Gerar uma chave: `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`

### 2. Comandos do deploy

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_questoes      # só na primeira vez
python manage.py collectstatic --noinput
gunicorn notamil_web.wsgi           # ou o Procfile incluído
```

Confira a configuração com `python manage.py check --deploy`.

### 3. Banco de dados

O banco padrão é o **SQLite** (arquivo `db.sqlite3` na raiz do projeto) — basta
`migrate` e `seed_questoes`. Para **MySQL** (8.0+), defina `DJANGO_DB_ENGINE=mysql`; as
demais credenciais vêm do ambiente:

| Variável | Padrão | Exemplo |
| --- | --- | --- |
| `DJANGO_DB_NAME` | `notamil` | `notamil` |
| `DJANGO_DB_USER` | `root` | `notamil_app` |
| `DJANGO_DB_PASSWORD` | *(vazio)* | *(senha do usuário)* |
| `DJANGO_DB_HOST` | `127.0.0.1` | `db.escola.br` |
| `DJANGO_DB_PORT` | `3306` | `3306` |
| `DJANGO_DB_ENGINE` | `sqlite` | `mysql` para usar o MySQL |

Crie o banco com acentuação correta antes do primeiro `migrate`:

```sql
CREATE DATABASE notamil CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'notamil_app'@'%' IDENTIFIED BY 'senha-forte';
GRANT ALL PRIVILEGES ON notamil.* TO 'notamil_app'@'%';
FLUSH PRIVILEGES;
```

Depois: `python manage.py migrate` e `python manage.py seed_questoes`.
O driver `mysqlclient` já está no `requirements.txt` (no Linux pode exigir
`sudo apt install python3-dev default-libmysqlclient-dev build-essential`).

Para levar os dados do SQLite para o MySQL:

```bash
python manage.py dumpdata simulados --indent 2 > dados.json
DJANGO_DB_ENGINE=mysql python manage.py migrate
DJANGO_DB_ENGINE=mysql python manage.py loaddata dados.json
```

### 4. Pontos de atenção
- **Questões**: rode `seed_questoes` uma vez no servidor, senão o banco nasce vazio.
- **QR Code**: ele aponta para o endereço usado para abrir a página, então funciona
  automaticamente depois de hospedado (e a turma consegue escanear de qualquer lugar).
- **Sem login**: a tentativa fica presa à sessão de quem a criou — o link não abre em
  outro navegador. Ainda assim é um simulado de estudo, não uma prova valendo nota com
  identificação de aluno (limpar os cookies perde o acesso às tentativas antigas).
- **Faxina**: agende `limpar_tentativas` (veja [Proteção contra abuso](#proteção-contra-abuso)),
  senão as tentativas abandonadas se acumulam.

## Proteção contra abuso

O app não tem login: qualquer pessoa pode pedir uma prova. Como cada prova gerada grava
uma `Tentativa` mais uma linha por questão sorteada, um script em laço encheria o banco.
As barreiras são estas:

| Onde | Proteção | Ajuste |
| --- | --- | --- |
| `forms.py` | Teto de **90 questões por área** e **180 por prova**. Sem ele, um POST com `quantidade_matematica=10**9` viraria um `SELECT` gigante. | `GerarProvaForm.MAX_POR_AREA` / `MAX_TOTAL` |
| `services/protecao_service.py` | Limite por IP: **20 provas/hora** em `/gerar-prova/` e **40/hora** em `/entrar-com-codigo/`. | `LIMITES` |
| `services/protecao_service.py` | A tentativa é gravada na sessão; `/simulado/`, `/resultado/` e `/analisar/` devolvem 404 para quem não a criou. | `MAX_TENTATIVAS_LEMBRADAS` |
| `services/prova_service.py` | O sorteio usa `random.sample` sobre os ids em vez de `ORDER BY RAND()`, que percorre e ordena a tabela inteira a cada prova. | — |
| `views.py` | A correção só abre com a prova **finalizada**. Antes disso dava para ler o gabarito em `/analisar/` com a prova em branco, ou responder uma questão por vez e consultar o total de acertos em `/resultado/` até acertar todas. | — |
| `management/commands/limpar_tentativas.py` | Apaga tentativas antigas. | `--dias` |

> **Vários workers:** o limite por IP usa o cache do Django, que por padrão é local ao
> processo — com 4 workers do gunicorn o teto real fica 4x maior. Para um limite exato,
> configure `CACHES` com Redis ou Memcached compartilhado.

### Faxina das tentativas

```bash
python manage.py limpar_tentativas                      # abandonadas com +30 dias
python manage.py limpar_tentativas --dias 7
python manage.py limpar_tentativas --incluir-finalizadas --incluir-provas
```

`--incluir-provas` remove só os códigos de turma antigos que **ninguém respondeu**.
Agende no servidor (cron diário às 4h):

```cron
0 4 * * * cd /caminho/do/notamil_web && python manage.py limpar_tentativas >> /var/log/notamil-faxina.log 2>&1
```

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
    │   ├── protecao_service.py # limite por IP e posse da tentativa pela sessão
    │   ├── limpeza_service.py # remoção das tentativas antigas
    │   └── seed_service.py    # carga do banco de questões
    ├── management/commands/
    │   ├── seed_questoes.py
    │   └── limpar_tentativas.py
    ├── fixtures/questoes.json # banco inicial com 71 questões do ENEM
    ├── static/simulados/      # css, js e as 21 imagens das questões
    ├── templates/simulados/
    ├── forms.py · urls.py · views.py · admin.py · tests.py
```

## Telas

| Rota | Tela |
|---|---|
| `/` | Menu inicial |
| `/gerar-prova/` | Configuração do simulado |
| `/simulado/<uuid>/<n>/` | Resolução das questões |
| `/resultado/<uuid>/` | Acertos e aproveitamento *(só após finalizar)* |
| `/analisar/<uuid>/<n>/` | Revisão com gabarito *(só após finalizar)* |
| `/redacao/` | Redação (em desenvolvimento) |
| `/turma/<codigo>/` | Código gerado para compartilhar a prova |
| `/entrar-com-codigo/` | Entrada na prova da turma pelo código |

## Código de turma

Ao gerar uma prova, ligue a opção **Criar código**: o sorteio é congelado em uma
`ProvaCompartilhada` e o sistema devolve um código de 6 caracteres (sem `O`, `0`,
`I` e `1` para evitar confusão). Quem entrar com esse código em
`/entrar-com-codigo/` responde exatamente as mesmas questões, na mesma ordem — cada
pessoa com a sua própria tentativa. A tela do código mostra o resumo por área e
quantas pessoas já finalizaram.

## Testes

```bash
python manage.py test
```
