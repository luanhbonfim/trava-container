# =============================================================================
# SERVICES/ORACLE.PY — Controle da trigger Oracle (nome vem de ORACLE_TRIGGER)
#
# Por padrão usa python-oracledb em THIN mode (não precisa de Instant Client).
# ATENÇÃO: o THIN mode só suporta Oracle Database 12.1 ou superior. Se o banco
# for Oracle 11g (11.2), defina ORACLE_THICK=True no .env e instale o Instant
# Client (informe o caminho em ORACLE_LIB_DIR).
#
# Funções públicas:
#   status_trigger()   -> 'ENABLED' | 'DISABLED'
#   ativar_trigger()   -> ('ENABLED',  mensagem)
#   desativar_trigger()-> ('DISABLED', mensagem)
#   alternar_trigger() -> (novo_status, mensagem)  (faz o toggle)
# =============================================================================

import oracledb
from django.conf import settings

_client_initialized = False


class OracleConfigError(RuntimeError):
    """Configuração ausente/incorreta (usuário, senha, DSN...)."""


class TriggerNaoEncontrada(RuntimeError):
    """A trigger configurada não existe no banco."""


def _split_owner_nome(nome_qualificado):
    """'DONO.MINHA_TRIGGER' -> ('DONO', 'MINHA_TRIGGER')."""
    if '.' in nome_qualificado:
        owner, nome = nome_qualificado.split('.', 1)
    else:
        owner, nome = '', nome_qualificado
    return owner.strip().upper(), nome.strip().upper()


def _conexao():
    """Abre uma conexão Oracle usando as credenciais do settings.ORACLE."""
    global _client_initialized
    cfg = settings.ORACLE

    if not cfg['USER'] or not cfg['PASSWORD']:
        raise OracleConfigError(
            'Credenciais do Oracle não configuradas. Defina ORACLE_USER e '
            'ORACLE_PASSWORD no arquivo .env.'
        )

    # THICK mode (necessário para Oracle 11g): inicializa o Instant Client 1x.
    if cfg['THICK'] and not _client_initialized:
        lib = cfg['LIB_DIR'] or None
        oracledb.init_oracle_client(lib_dir=lib)
        _client_initialized = True

    return oracledb.connect(
        user=cfg['USER'],
        password=cfg['PASSWORD'],
        dsn=cfg['DSN'],
    )


def status_trigger():
    """
    Retorna o status atual da trigger: 'ENABLED' ou 'DISABLED'.
    Lança TriggerNaoEncontrada se ela não existir.
    """
    owner, nome = _split_owner_nome(settings.ORACLE['TRIGGER'])
    con = _conexao()
    try:
        cur = con.cursor()
        if owner:
            cur.execute(
                """
                SELECT STATUS
                FROM   ALL_TRIGGERS
                WHERE  OWNER = :owner AND TRIGGER_NAME = :nome
                """,
                owner=owner, nome=nome,
            )
        else:
            cur.execute(
                """
                SELECT STATUS
                FROM   USER_TRIGGERS
                WHERE  TRIGGER_NAME = :nome
                """,
                nome=nome,
            )
        linha = cur.fetchone()
        cur.close()
    finally:
        con.close()

    if linha is None:
        raise TriggerNaoEncontrada(
            f'Trigger {settings.ORACLE["TRIGGER"]} não encontrada no banco.'
        )
    return (linha[0] or '').strip().upper()


def _alterar(acao):
    """Executa ALTER TRIGGER ... ENABLE|DISABLE. DDL faz commit implícito."""
    assert acao in ('ENABLE', 'DISABLE')
    nome_qualificado = settings.ORACLE['TRIGGER']
    owner, nome = _split_owner_nome(nome_qualificado)
    alvo = f'{owner}.{nome}' if owner else nome

    con = _conexao()
    try:
        cur = con.cursor()
        # Identificadores não podem ser bind variables; o nome vem do settings
        # (não de entrada do usuário), então é seguro interpolar.
        cur.execute(f'ALTER TRIGGER {alvo} {acao}')
        cur.close()
    finally:
        con.close()


def ativar_trigger():
    """Ativa a trigger. Retorna ('ENABLED', mensagem)."""
    _alterar('ENABLE')
    return 'ENABLED', 'Trava ATIVADA com sucesso.'


def desativar_trigger():
    """Desativa a trigger. Retorna ('DISABLED', mensagem)."""
    _alterar('DISABLE')
    return 'DISABLED', 'Trava DESATIVADA com sucesso.'


def alternar_trigger():
    """
    Faz o toggle com base no status atual.
    Retorna (novo_status, mensagem).
    """
    atual = status_trigger()
    if atual == 'ENABLED':
        return desativar_trigger()
    return ativar_trigger()
