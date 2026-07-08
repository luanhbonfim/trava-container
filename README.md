# Trava do Peso do Container

Aplicação web em **Django** para **ativar/desativar** uma trigger Oracle
(a "trava" do peso do container), com **login por usuário**, **grupos/permissões**
e **registro de auditoria** (quem, quando, motivo, ação e resultado).

- Um único botão no painel que **alterna** o estado da trava.
- Antes de executar, pede **nome e motivo** (obrigatórios) para o log.
- **Login por usuário** e permissões por grupo (operar a trava / ver logs).
- Sessão com **janela de acesso** por tempo (contador na tela).
- Toda a configuração sensível fica no `.env` (nunca versionado).

> ⚠️ **Segredos:** host do banco, usuário/senha, DSN do Oracle e nome da trigger
> ficam **somente** no arquivo `.env` de cada ambiente. Nunca coloque valores
> reais neste README nem em qualquer arquivo versionado.

---

## Configuração (`.env`)

Crie um `.env` a partir dos nomes de variáveis abaixo (preencha com os valores
reais do seu ambiente — não versione este arquivo):

```ini
SECRET_KEY=<gere: python -c "import secrets;print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=<ip-do-servidor>,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://<ip-do-servidor>:<porta>
SECURE_SSL=False

# Banco (deixe DB_NAME vazio para usar SQLite em dev)
DB_NAME=<nome-do-banco>
DB_USER=<usuario>
DB_PASSWORD=<senha>
DB_HOST=localhost
DB_PORT=<porta-postgres>
DB_SCHEMA=

# Oracle
ORACLE_USER=<usuario-oracle>
ORACLE_PASSWORD=<senha-oracle>
ORACLE_DSN=<host>:<porta>/<servico>
ORACLE_TRIGGER=<OWNER>.<NOME_DA_TRIGGER>
ORACLE_THICK=True
ORACLE_LIB_DIR=/opt/oracle/instantclient
```

> O usuário Oracle precisa de privilégio para alterar a trigger
> (`ALTER ANY TRIGGER`, ou ser o dono do schema, ou ter `ALTER` sobre a tabela base).

### ⚠️ Oracle 11g

O **thin mode** do `python-oracledb` só suporta **Oracle 12.1+**. Para **Oracle 11g**,
use thick mode: `ORACLE_THICK=True` e `ORACLE_LIB_DIR` apontando para o Instant Client.

---

## Rodar em desenvolvimento (Windows, SQLite)

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 manage.py migrate
py -3.14 manage.py createsuperuser
py -3.14 manage.py runserver 0.0.0.0:8000
```

Sem `DB_NAME` no `.env`, usa SQLite automaticamente.

---

## Deploy no Linux (Postgres + gunicorn)

O app cria ~10 tabelas do Django. Para conviver com outro projeto no mesmo
Postgres, use um **banco separado** (recomendado) ou um **schema separado**
(`DB_SCHEMA`).

### 1. Dependências do sistema (Debian/Ubuntu)
```bash
apt update && apt install -y python3-venv python3-pip libaio1   # libaio1t64 no Ubuntu 24+
# Instant Client em /opt/oracle/instantclient (thick mode p/ Oracle 11g)
```

### 2. Código (via git) e ambiente
```bash
git clone <url-do-repositorio> /opt/peso_container
cd /opt/peso_container
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Banco (Opção A — banco separado)
```bash
su - postgres -c "psql -p <porta> -c 'CREATE DATABASE <nome-do-banco> OWNER <usuario>;'"
```

### 4. `.env`
Crie o `.env` no servidor (ver seção "Configuração"). Ele **não** vem do git.

### 5. Migrar, grupos, estáticos e usuário
```bash
python manage.py migrate
python manage.py setup_grupos      # cria Operadores / Auditoria / Gestores
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 6. Serviço systemd
`/etc/systemd/system/peso-container.service`:
```ini
[Unit]
Description=Peso Container (trava)
After=network.target

[Service]
User=root
WorkingDirectory=/opt/peso_container
ExecStart=/opt/peso_container/.venv/bin/gunicorn peso_container.wsgi:application --bind 0.0.0.0:<porta> --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable --now peso-container
```
Libere a porta no firewall se necessário: `ufw allow <porta>/tcp`.

> **WhiteNoise** serve o CSS pelo próprio gunicorn (após `collectstatic`) — não
> precisa de Nginx só para estáticos.

---

## Atualizar (fluxo git)
```bash
cd /opt/peso_container && git pull
source .venv/bin/activate
pip install -r requirements.txt   # só se mudou dependência
python manage.py migrate          # só se houver migração nova
systemctl restart peso-container
```
O `.env` do servidor não é tocado pelo git (está no `.gitignore`).

---

## Permissões

| Grupo | Operar a trava | Ver logs |
|---|:---:|:---:|
| Operadores | ✅ | — |
| Auditoria | — | ✅ |
| Gestores | ✅ | ✅ |

Superusuário tem acesso total. Associe usuários aos grupos em `/admin/`.

## Estrutura
```
├─ manage.py
├─ requirements.txt
├─ peso_container/        # settings, urls, wsgi
├─ core/
│  ├─ models.py           # LogTrigger (auditoria)
│  ├─ views.py            # painel, alternar, logs
│  ├─ services/oracle.py  # conexão Oracle + ALTER TRIGGER
│  └─ management/commands/setup_grupos.py
├─ templates/
└─ static/css/style.css
```

## Como usar
1. Faça **login**.
2. No painel aparece o status da trava (ATIVADA / DESATIVADA).
3. Clique para alternar, informe **nome e motivo**, confirme.
4. A ação é executada no Oracle e **registrada em log** (visível em `/logs/` e no `/admin/`).
