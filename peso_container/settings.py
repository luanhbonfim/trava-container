"""
Configurações do projeto PESO_CONTAINER.

Aplicação web simples (Django) para ativar/desativar uma trigger Oracle
(a "trava" do peso do container), com login por usuário e registro de logs.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis do arquivo .env (se existir)
load_dotenv(BASE_DIR / '.env')


def _env_bool(nome, padrao=False):
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ('1', 'true', 'yes', 'on', 'sim')


# -----------------------------------------------------------------------------
# Segurança
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'dev-inseguro-troque-no-.env-antes-de-ir-para-producao',
)

DEBUG = _env_bool('DEBUG', True)

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()
] or ['*']

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

# -----------------------------------------------------------------------------
# Aplicações
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serve os arquivos estáticos (CSS) mesmo com DEBUG=False, sem nginx.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'peso_container.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.sessao',
            ],
        },
    },
]

WSGI_APPLICATION = 'peso_container.wsgi.application'

# -----------------------------------------------------------------------------
# Banco do próprio app (usuários/sessões/logs). O Oracle é acessado à parte,
# via core/services/oracle.py.
#
# Se DB_NAME estiver definido no .env, usa PostgreSQL; caso contrário, SQLite
# (bom para desenvolvimento local no Windows).
#
# DB_SCHEMA (opcional): coloca TODAS as tabelas do app num schema separado do
# Postgres (ex.: 'peso'), útil para conviver com outro projeto no mesmo banco.
# O schema precisa existir antes do migrate (CREATE SCHEMA ...).
# -----------------------------------------------------------------------------
if os.getenv('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.getenv('DB_NAME'),
            'USER':     os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST':     os.getenv('DB_HOST', 'localhost'),
            'PORT':     os.getenv('DB_PORT', '5432'),
        }
    }
    _db_schema = os.getenv('DB_SCHEMA', '').strip()
    if _db_schema:
        DATABASES['default']['OPTIONS'] = {
            'options': f'-c search_path={_db_schema}',
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -----------------------------------------------------------------------------
# Oracle (trigger definida em ORACLE_TRIGGER)
# -----------------------------------------------------------------------------
ORACLE = {
    'USER':     os.getenv('ORACLE_USER', ''),
    'PASSWORD': os.getenv('ORACLE_PASSWORD', ''),
    'DSN':      os.getenv('ORACLE_DSN', ''),
    # THIN mode por padrão. Oracle 11g exige THICK (Instant Client).
    'THICK':    _env_bool('ORACLE_THICK', False),
    'LIB_DIR':  os.getenv('ORACLE_LIB_DIR', ''),
    # Nome totalmente qualificado da trigger a controlar (vem do .env).
    'TRIGGER':  os.getenv('ORACLE_TRIGGER', ''),
}

# -----------------------------------------------------------------------------
# Validação de senha
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# Internacionalização
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Arquivos estáticos
# -----------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------------------------------------------------------
# Autenticação
# -----------------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'painel'
LOGOUT_REDIRECT_URL = 'login'

# Janela de acesso de SEGURANÇA (absoluta): a sessão vale por 1 minuto
# contado a partir do login e NÃO é renovada por atividade — passou o tempo,
# é preciso logar de novo. Também expira ao fechar o navegador.
# (SESSION_SAVE_EVERY_REQUEST fica desligado de propósito para não renovar.)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60  # 1 minuto (janela única de acesso)

# Endurecimento HTTPS opcional (rede interna sem TLS: manter False)
if _env_bool('SECURE_SSL', False):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
