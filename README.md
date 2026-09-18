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

O padrão é **SQLite** (`db.sqlite3`), que fica fora do Git e basta para desenvolvimento.
Em hosts com disco efêmero (Render free, por exemplo) os resultados somem a cada deploy.

Para usar **MySQL**, basta definir as variáveis abaixo — a presença de `DJANGO_DB_NAME`
já troca o banco, sem mexer em código:

| Variável | Exemplo |
| --- | --- |
| `DJANGO_DB_NAME` | `notamil` |
| `DJANGO_DB_USER` | `notamil_app` |
| `DJANGO_DB_PASSWORD` | *(senha do usuário)* |
| `DJANGO_DB_HOST` | `127.0.0.1` |
| `DJANGO_DB_PORT` | `3306` |

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

Para levar os dados que já existem no SQLite:

```bash
python manage.py dumpdata simulados --indent 2 > dados.json   # sem as variaveis do MySQL
# com as variaveis do MySQL definidas:
python manage.py migrate
python manage.py loaddata dados.json
```

### 4. Pontos de atenção
- **Questões**: rode `seed_questoes` uma vez no servidor, senão o banco nasce vazio.
- **QR Code**: ele aponta para o endereço usado para abrir a página, então funciona
  automaticamente depois de hospedado (e a turma consegue escanear de qualquer lugar).
- **Sem login**: quem tiver o link de uma tentativa consegue abri-la. É um simulado de
  estudo, não uma prova valendo nota com identificação de aluno.

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
