"""
Testes do app core (PESO_CONTAINER).

O Oracle é sempre "mockado" — os testes NÃO se conectam ao banco real.
Cobrem: autenticação obrigatória, exibição de status, regra do nome,
toggle correto (ativa/desativa), registro de log em sucesso e falha,
e o parsing de nome da trigger no serviço.
"""
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from core.models import LogTrigger


def _dar_permissao(user, *codenames):
    """Concede permissões do app 'core' ao usuário."""
    perms = Permission.objects.filter(
        codename__in=codenames, content_type__app_label='core'
    )
    user.user_permissions.add(*perms)


class AutenticacaoTests(TestCase):
    """Todas as telas exigem login."""

    def test_painel_redireciona_sem_login(self):
        resp = self.client.get(reverse('painel'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_logs_redireciona_sem_login(self):
        resp = self.client.get(reverse('logs'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_alternar_redireciona_sem_login(self):
        resp = self.client.post(reverse('alternar'), {'nome_informado': 'X'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])
        self.assertEqual(LogTrigger.objects.count(), 0)


class PainelTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('operador', password='senha123')
        _dar_permissao(user, 'pode_operar_trava')
        self.client.login(username='operador', password='senha123')

    @mock.patch('core.views.oracle.status_trigger', return_value='DISABLED')
    def test_mostra_desativada(self, _m):
        resp = self.client.get(reverse('painel'))
        self.assertContains(resp, 'TRAVA DESATIVADA')
        self.assertContains(resp, 'Ativar trava')

    @mock.patch('core.views.oracle.status_trigger', return_value='ENABLED')
    def test_mostra_ativada(self, _m):
        resp = self.client.get(reverse('painel'))
        self.assertContains(resp, 'TRAVA ATIVADA')
        self.assertContains(resp, 'Desativar trava')

    def test_erro_nao_vaza_termo_tecnico(self):
        # Usa a exceção REAL do serviço, cuja mensagem inclui o nome da trigger.
        from core.services import oracle
        erro_real = oracle.TriggerNaoEncontrada(
            'Trigger DONO.TRG_EXEMPLO não encontrada no banco.'
        )
        with mock.patch('core.views.oracle.status_trigger', side_effect=erro_real):
            resp = self.client.get(reverse('painel'))
        self.assertContains(resp, 'Sistema indisponível')
        # O nome técnico da trigger nunca deve aparecer para o usuário
        self.assertNotContains(resp, 'TRG_EXEMPLO')
        self.assertNotContains(resp, 'DONO')
        self.assertNotContains(resp, 'trigger')


class AlternarTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('operador', password='senha123')
        _dar_permissao(user, 'pode_operar_trava')
        self.client.login(username='operador', password='senha123')

    def test_sem_permissao_403(self):
        User.objects.create_user('visitante', password='senha123')
        self.client.login(username='visitante', password='senha123')
        with mock.patch('core.views.oracle.status_trigger', return_value='DISABLED'), \
             mock.patch('core.views.oracle.ativar_trigger') as ativar:
            resp = self.client.post(reverse('alternar'),
                                    {'nome_informado': 'X', 'motivo': 'Y'})
            ativar.assert_not_called()
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(LogTrigger.objects.count(), 0)

    def test_get_nao_permitido(self):
        resp = self.client.get(reverse('alternar'))
        self.assertEqual(resp.status_code, 405)

    def test_sem_nome_nao_executa_e_nao_registra(self):
        with mock.patch('core.views.oracle.status_trigger', return_value='DISABLED'), \
             mock.patch('core.views.oracle.ativar_trigger') as ativar, \
             mock.patch('core.views.oracle.desativar_trigger') as desativar:
            self.client.post(reverse('alternar'),
                             {'nome_informado': '   ', 'motivo': 'teste'})
            ativar.assert_not_called()
            desativar.assert_not_called()
        self.assertEqual(LogTrigger.objects.count(), 0)

    def test_sem_motivo_nao_executa_e_nao_registra(self):
        with mock.patch('core.views.oracle.status_trigger', return_value='DISABLED'), \
             mock.patch('core.views.oracle.ativar_trigger') as ativar, \
             mock.patch('core.views.oracle.desativar_trigger') as desativar:
            self.client.post(reverse('alternar'),
                             {'nome_informado': 'João', 'motivo': '   '})
            ativar.assert_not_called()
            desativar.assert_not_called()
        self.assertEqual(LogTrigger.objects.count(), 0)

    def test_ativa_quando_desabilitada(self):
        with mock.patch('core.views.oracle.status_trigger', return_value='DISABLED'), \
             mock.patch('core.views.oracle.ativar_trigger',
                        return_value=('ENABLED', 'Trava ATIVADA com sucesso.')) as ativar, \
             mock.patch('core.views.oracle.desativar_trigger') as desativar:
            self.client.post(reverse('alternar'),
                             {'nome_informado': 'João Silva', 'motivo': 'Manutenção da balança'})
            ativar.assert_called_once()
            desativar.assert_not_called()

        log = LogTrigger.objects.get()
        self.assertEqual(log.acao, LogTrigger.ACAO_ATIVAR)
        self.assertTrue(log.sucesso)
        self.assertEqual(log.nome_informado, 'João Silva')
        self.assertEqual(log.motivo, 'Manutenção da balança')
        self.assertEqual(log.status_anterior, 'DISABLED')
        self.assertEqual(log.status_final, 'ENABLED')
        self.assertEqual(log.usuario.username, 'operador')

    def test_desativa_quando_habilitada(self):
        with mock.patch('core.views.oracle.status_trigger', return_value='ENABLED'), \
             mock.patch('core.views.oracle.desativar_trigger',
                        return_value=('DISABLED', 'Trava DESATIVADA com sucesso.')) as desativar, \
             mock.patch('core.views.oracle.ativar_trigger') as ativar:
            self.client.post(reverse('alternar'),
                             {'nome_informado': 'Maria', 'motivo': 'Liberar exportação'})
            desativar.assert_called_once()
            ativar.assert_not_called()

        log = LogTrigger.objects.get()
        self.assertEqual(log.acao, LogTrigger.ACAO_DESATIVAR)
        self.assertTrue(log.sucesso)
        self.assertEqual(log.motivo, 'Liberar exportação')
        self.assertEqual(log.status_anterior, 'ENABLED')
        self.assertEqual(log.status_final, 'DISABLED')

    def test_falha_na_operacao_registra_log_de_falha(self):
        with mock.patch('core.views.oracle.status_trigger', return_value='DISABLED'), \
             mock.patch('core.views.oracle.ativar_trigger',
                        side_effect=Exception('ORA-01031: insufficient privileges')):
            self.client.post(reverse('alternar'),
                             {'nome_informado': 'João', 'motivo': 'teste'})

        log = LogTrigger.objects.get()
        self.assertFalse(log.sucesso)
        self.assertEqual(log.acao, LogTrigger.ACAO_ATIVAR)
        self.assertEqual(log.motivo, 'teste')
        self.assertIn('ORA-01031', log.mensagem)  # detalhe técnico fica no log
        self.assertEqual(log.status_anterior, 'DISABLED')

    def test_erro_ao_ler_status_nao_registra(self):
        with mock.patch('core.views.oracle.status_trigger',
                        side_effect=Exception('sem conexão')):
            self.client.post(reverse('alternar'),
                             {'nome_informado': 'João', 'motivo': 'teste'})
        self.assertEqual(LogTrigger.objects.count(), 0)


class OracleServicoTests(TestCase):
    """Testes de unidade do serviço, sem tocar no banco Oracle real."""

    def test_split_owner_nome(self):
        from core.services import oracle
        self.assertEqual(
            oracle._split_owner_nome('DONO.MINHA_TRIGGER'),
            ('DONO', 'MINHA_TRIGGER'),
        )
        self.assertEqual(
            oracle._split_owner_nome('trg_teste'),
            ('', 'TRG_TESTE'),
        )

    def test_status_trigger_nao_encontrada(self):
        from core.services import oracle
        cursor = mock.MagicMock()
        cursor.fetchone.return_value = None
        con = mock.MagicMock()
        con.cursor.return_value = cursor
        with mock.patch('core.services.oracle._conexao', return_value=con):
            with self.assertRaises(oracle.TriggerNaoEncontrada):
                oracle.status_trigger()
        con.close.assert_called_once()

    def test_status_trigger_le_valor(self):
        from core.services import oracle
        cursor = mock.MagicMock()
        cursor.fetchone.return_value = ('ENABLED',)
        con = mock.MagicMock()
        con.cursor.return_value = cursor
        with mock.patch('core.services.oracle._conexao', return_value=con):
            self.assertEqual(oracle.status_trigger(), 'ENABLED')

    def test_ativar_executa_alter_enable(self):
        from core.services import oracle
        from django.test import override_settings
        cfg = dict(oracle.settings.ORACLE)
        cfg['TRIGGER'] = 'DONO.TRG_TESTE'
        cursor = mock.MagicMock()
        con = mock.MagicMock()
        con.cursor.return_value = cursor
        with override_settings(ORACLE=cfg), \
             mock.patch('core.services.oracle._conexao', return_value=con):
            status, _msg = oracle.ativar_trigger()
        self.assertEqual(status, 'ENABLED')
        sql = cursor.execute.call_args[0][0]
        self.assertIn('ENABLE', sql)
        self.assertIn('DONO.TRG_TESTE', sql)

    def test_conexao_sem_credenciais_falha(self):
        from core.services import oracle
        from django.test import override_settings
        cfg = dict(oracle.settings.ORACLE)
        cfg['USER'] = ''
        cfg['PASSWORD'] = ''
        with override_settings(ORACLE=cfg):
            with self.assertRaises(oracle.OracleConfigError):
                oracle._conexao()


class LogsPermissaoTests(TestCase):
    def test_sem_permissao_403(self):
        User.objects.create_user('visitante', password='senha123')
        self.client.login(username='visitante', password='senha123')
        resp = self.client.get(reverse('logs'))
        self.assertEqual(resp.status_code, 403)

    def test_com_permissao_200(self):
        user = User.objects.create_user('auditor', password='senha123')
        _dar_permissao(user, 'pode_ver_logs')
        self.client.login(username='auditor', password='senha123')
        resp = self.client.get(reverse('logs'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Logs de auditoria')


class SessaoTests(TestCase):
    def test_admin_tem_sessao_longa(self):
        User.objects.create_user('ti', password='senha123', is_staff=True)
        self.client.login(username='ti', password='senha123')
        # muito acima de 60s (janela operacional)
        self.assertGreater(self.client.session.get_expiry_age(), 3600)

    def test_operador_tem_janela_de_1min(self):
        User.objects.create_user('op', password='senha123')
        self.client.login(username='op', password='senha123')
        self.assertLessEqual(self.client.session.get_expiry_age(), 60)


class HostnameTests(TestCase):
    def test_hostname_resolve(self):
        from core import views
        with mock.patch('core.views.socket.gethostbyaddr',
                        return_value=('PC-EXPORT01', [], ['10.10.1.50'])):
            self.assertEqual(views._hostname('10.10.1.50'), 'PC-EXPORT01')

    def test_hostname_falha_retorna_vazio(self):
        from core import views
        with mock.patch('core.views.socket.gethostbyaddr',
                        side_effect=OSError('no PTR')):
            self.assertEqual(views._hostname('10.10.1.50'), '')

    def test_hostname_sem_ip(self):
        from core import views
        self.assertEqual(views._hostname(''), '')
        self.assertEqual(views._hostname(None), '')


class AdminPermissoesTests(TestCase):
    def test_admin_so_oferece_permissoes_do_app(self):
        from core.admin import _queryset_permissoes_app
        qs = _queryset_permissoes_app()
        self.assertEqual(
            set(qs.values_list('codename', flat=True)),
            {'pode_operar_trava', 'pode_ver_logs'},
        )

    def test_admin_data_hora_formato(self):
        import re
        from django.contrib.admin.sites import site
        from core.admin import LogTriggerAdmin
        log = LogTrigger.objects.create(
            nome_informado='x', motivo='y', acao=LogTrigger.ACAO_ATIVAR, sucesso=True,
        )
        texto = LogTriggerAdmin(LogTrigger, site).data_hora(log)
        self.assertRegex(texto, r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$')


class GruposCommandTests(TestCase):
    def test_setup_grupos_cria_grupos_com_permissoes(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        call_command('setup_grupos')
        self.assertTrue(Group.objects.filter(name='Operadores').exists())
        self.assertTrue(Group.objects.filter(name='Auditoria').exists())
        gestores = Group.objects.get(name='Gestores')
        codes = set(gestores.permissions.values_list('codename', flat=True))
        self.assertEqual(codes, {'pode_operar_trava', 'pode_ver_logs'})
