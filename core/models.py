from django.conf import settings
from django.db import models


class LogTrigger(models.Model):
    """
    Registro de auditoria de cada tentativa de ativar/desativar a trigger.
    Guarda quem fez (usuário logado), o nome informado no momento, a ação,
    o status resultante, se deu certo e uma mensagem.
    """

    ACAO_ATIVAR = 'ENABLE'
    ACAO_DESATIVAR = 'DISABLE'
    ACOES = [
        (ACAO_ATIVAR, 'Ativar'),
        (ACAO_DESATIVAR, 'Desativar'),
    ]

    criado_em = models.DateTimeField('Data/Hora', auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Usuário (login)',
    )
    nome_informado = models.CharField(
        'Nome informado', max_length=150,
        help_text='Nome digitado por quem executou a ação.',
    )
    motivo = models.CharField(
        'Motivo', max_length=255, default='', blank=True,
        help_text='Motivo informado por quem executou a ação.',
    )
    acao = models.CharField('Ação', max_length=10, choices=ACOES)
    status_anterior = models.CharField('Status anterior', max_length=20, blank=True)
    status_final = models.CharField('Status final', max_length=20, blank=True)
    sucesso = models.BooleanField('Sucesso', default=False)
    mensagem = models.TextField('Mensagem', blank=True)
    ip = models.GenericIPAddressField('IP de origem', null=True, blank=True)

    class Meta:
        verbose_name = 'Log da Trigger'
        verbose_name_plural = 'Logs da Trigger'
        ordering = ['-criado_em']
        permissions = [
            ('pode_operar_trava', 'Pode travar e destravar'),
            ('pode_ver_logs', 'Pode ver os logs'),
        ]

    def __str__(self):
        estado = 'OK' if self.sucesso else 'FALHA'
        return f'[{estado}] {self.get_acao_display()} por {self.nome_informado} em {self.criado_em:%d/%m/%Y %H:%M}'
