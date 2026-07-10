"""
Ajusta a data/hora do log:
  - remove a precisão de frações de segundo da coluna criado_em (timestamp(0));
  - cria a VIEW vw_logs_trava com a data já formatada como dd/mm/yyyy hh:mm:ss
    (horário de São Paulo) para consultas diretas no banco.

Só tem efeito no PostgreSQL; no SQLite (dev/testes) é no-op.
"""
from django.db import migrations

VIEW_SQL = """
CREATE OR REPLACE VIEW vw_logs_trava AS
SELECT
    l.id,
    to_char(l.criado_em AT TIME ZONE 'America/Sao_Paulo',
            'DD/MM/YYYY HH24:MI:SS')                          AS data_hora,
    CASE l.acao
        WHEN 'ENABLE'  THEN 'Ativar'
        WHEN 'DISABLE' THEN 'Desativar'
        ELSE l.acao
    END                                                       AS acao,
    l.nome_informado,
    l.motivo,
    u.username                                                AS usuario,
    l.status_anterior,
    l.status_final,
    l.sucesso,
    l.ip,
    l.hostname,
    l.mensagem
FROM core_logtrigger l
LEFT JOIN auth_user u ON u.id = l.usuario_id
ORDER BY l.criado_em DESC;
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        'ALTER TABLE core_logtrigger '
        'ALTER COLUMN criado_em TYPE timestamp(0) with time zone'
    )
    schema_editor.execute(VIEW_SQL)


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute('DROP VIEW IF EXISTS vw_logs_trava')
    schema_editor.execute(
        'ALTER TABLE core_logtrigger '
        'ALTER COLUMN criado_em TYPE timestamp(6) with time zone'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_logtrigger_hostname'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
