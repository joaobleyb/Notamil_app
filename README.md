# NotaMil

Simulador de provas no estilo ENEM, feito com **Django + Bootstrap 5**.
O fluxo é: gerar prova → resolver → resultado → analisar tentativa.

## Recursos

- Sorteio de questões por área (Linguagens, Humanas, Natureza, Matemática) e idioma estrangeiro.
- Código de turma: a turma inteira responde exatamente a mesma prova.
- Embaralhar por aluno (opcional): mesmas questões, ordem diferente em cada prova — evita cola.
- QR Code do código, para a turma entrar pela câmera do celular.
- Correção automática com análise questão a questão.
- Navegação livre entre as questões: botão Anterior e índice numerado com salto
  direto, marcando o que já foi respondido.
- Só finaliza com a prova inteira respondida — a validação é no servidor, não só no
  formulário.
- Proteções contra uso abusivo: teto de questões por prova, limite por IP,
  tentativa presa à sessão e faxina das tentativas antigas.

## Como rodar

Depois de baixar o projeto do GitHub, entre na pasta `notamil_web` e rode o script da
sua plataforma. Ele cria o ambiente virtual, instala as dependências, prepara o banco,
carrega as 2643 questões do ENEM na primeira execução e sobe o servidor em
<http://127.0.0.1:8000/>. Nas próximas vezes ele só liga o servidor.

### macOS e Linux

Dê **dois cliques** em `iniciar.command`, ou no terminal:

```bash
./iniciar.command
```

Para parar: `Control + C`.

> Se o duplo clique não abrir, o arquivo perdeu a permissão de execução no caminho até a
> sua máquina. Rode uma vez `chmod +x iniciar.command` na pasta do projeto.

### Windows

Dê **dois cliques** em `iniciar.bat`, ou no terminal, dentro da pasta:

```bat
iniciar
```

Para parar: `Ctrl + C`.

### Manualmente, passo a passo

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_questoes     # carrega as 2643 questões do ENEM
python manage.py runserver
```

O banco padrão é o **SQLite** do próprio Django: não precisa instalar nem ligar nada.
Para usar **MySQL** (veja [Hospedagem](#hospedagem)), defina
`DJANGO_DB_ENGINE=mysql` e as credenciais.

Acesse <http://127.0.0.1:8000/>.

Para usar o admin (`/admin/`): `python manage.py createsuperuser`.

> Em desenvolvimento, rode com `DJANGO_DEBUG=1` (no PowerShell: `$env:DJANGO_DEBUG="1"`).
> Sem ele o CSS vem da cópia em `staticfiles/`, e só muda depois de `collectstatic`.
> Sem essa variável o projeto assume modo de produção.

## Hospedagem

Passo a passo do deploy em um servidor Ubuntu com Nginx. Os arquivos estáticos são
servidos pelo próprio Django via WhiteNoise, então não é preciso configurar o Nginx para
o CSS e as imagens.

Em produção use **MySQL**, não o SQLite. O SQLite é um arquivo local: se o site roda em
mais de uma instância, cada uma fica com a sua própria cópia, e a prova gerada em uma
não existe na outra — gerar a prova funciona, mas a tela seguinte devolve **404 Not
Found**. Em hosts de disco efêmero, como Render e Railway, o arquivo ainda é descartado
a cada deploy, levando junto as tentativas dos alunos.

### 1. Instalar o MySQL

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
```

### 2. Criar o banco e o usuário

```bash
sudo mysql
```

```sql
CREATE DATABASE notamil CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'notamil_app'@'localhost' IDENTIFIED BY 'TROQUE-ESTA-SENHA';
GRANT ALL PRIVILEGES ON notamil.* TO 'notamil_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> Em contêineres Docker, troque `'localhost'` por `'%'` e use o IP do host (ou o nome do
> serviço no compose) no `DJANGO_DB_HOST` — de dentro do contêiner, `127.0.0.1` aponta
> para ele mesmo, não para o MySQL.

### 3. Instalar as dependências

```bash
sudo apt install -y python3-dev default-libmysqlclient-dev build-essential pkg-config
```

Na venv de **cada instância** da aplicação:

```bash
pip install -r requirements.txt
pip install -r requirements-mysql.txt     # driver do MySQL
```

### 4. Variáveis de ambiente

Gere a chave secreta — **uma só**, a mesma para todas as instâncias:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Crie `/etc/notamil.env` com o domínio real do site:

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=cole-a-chave-gerada-aqui
DJANGO_ALLOWED_HOSTS=notamil.escola.br
DJANGO_CSRF_ORIGINS=https://notamil.escola.br
DJANGO_DB_ENGINE=mysql
DJANGO_DB_NAME=notamil
DJANGO_DB_USER=notamil_app
DJANGO_DB_PASSWORD=TROQUE-ESTA-SENHA
DJANGO_DB_HOST=127.0.0.1
DJANGO_DB_PORT=3306
```

```bash
sudo chmod 600 /etc/notamil.env
```

Quatro delas não são opcionais:

- `DJANGO_DEBUG=0` — nunca `1` em produção.
- `DJANGO_SECRET_KEY` — sem ela cada processo sorteia uma chave nova a cada reinício, e
  o login do admin cai sozinho. Use a mesma em todas as instâncias.
- `DJANGO_ALLOWED_HOSTS` — sem o domínio aqui, o site responde erro 400.
- `DJANGO_CSRF_ORIGINS` — obrigatória em HTTPS, senão os formulários dão erro 403.

Opcional: `DJANGO_SSL_REDIRECT=1` força http → https (deixe fora se o Nginx já
redireciona).

### 5. Preparar o banco — uma vez só

```bash
set -a; . /etc/notamil.env; set +a     # carrega as variáveis no shell
cd /caminho/do/notamil_web
source .venv/bin/activate
python manage.py migrate
python manage.py seed_questoes          # as 2643 questões; sem isso o banco nasce vazio
python manage.py collectstatic --noinput
```

Com várias instâncias, isto roda em **uma** delas: todas leem o mesmo banco.

### 6. Subir a aplicação

O `Procfile` incluído já serve: `gunicorn notamil_web.wsgi`. Ligue o arquivo de
variáveis em **todas** as instâncias:

- **systemd** — em cada unit, na seção `[Service]`: `EnvironmentFile=/etc/notamil.env`,
  depois `sudo systemctl daemon-reload` e `sudo systemctl restart <serviço>`.
- **Docker Compose** — em cada serviço: `env_file: /etc/notamil.env`, depois
  `docker compose up -d --force-recreate`.

### 7. Verificar

```bash
python manage.py check --deploy
python manage.py shell -c "from simulados.models import Questao, Tentativa; print(Questao.objects.count(), Tentativa.objects.count())"
```

O esperado é `2643 0`. Com várias instâncias, rode o segundo comando em cada uma: os
números têm que ser iguais. Depois gere uma prova pelo site e repita — se o contador de
tentativas subir em **todas**, o banco está compartilhado.

Se ainda aparecer 404 ao abrir a prova, repita a mesma URL com o mesmo cookie umas doze
vezes: alternar entre `200` e `404` significa que as instâncias continuam em bancos
separados, e a proporção indica quantas são.

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
| `views.py` | Finalizar exige **todas as questões respondidas**. O `required` do HTML cobre só a questão da tela e o aluno contorna; a checagem que vale é a do servidor, via `ordens_pendentes`. | — |
| `views.py` | A correção só abre com a prova **finalizada**. Antes disso dava para ler o gabarito em `/analisar/` com a prova em branco, ou responder uma questão por vez e consultar o total de acertos em `/resultado/` até acertar todas. | — |
| `management/commands/limpar_tentativas.py` | Apaga tentativas antigas. | `--dias` |

> **Vários workers:** o limite por IP usa o cache do Django, que por padrão é local ao
> processo — com 4 workers do gunicorn o teto real fica 4x maior (e o mesmo vale
> para cada instância, veja [Hospedagem](#hospedagem)). Para um limite exato,
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
├── iniciar.command            # instala e roda tudo com um comando (macOS, Linux)
├── iniciar.bat                # o mesmo, no Windows
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
    ├── fixtures/questoes.json # banco inicial com 2643 questões do ENEM
    ├── static/simulados/      # css, js e as 1014 imagens das questões
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
