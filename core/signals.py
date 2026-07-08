import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def definir_janela_de_acesso(sender, request, user, **kwargs):
    """
    Define uma janela de acesso ABSOLUTA no momento do login: a sessão
    expira SESSION_COOKIE_AGE segundos depois, sem renovar por atividade.

    Guarda o instante-limite (epoch) para o contador da tela mostrar o
    tempo real restante, e fixa a expiração da sessão no servidor.
    """
    if request is None:
        return
    request.session['expira_epoch'] = int(time.time()) + settings.SESSION_COOKIE_AGE
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
