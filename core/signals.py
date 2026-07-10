import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

# Sessão "ilimitada" para admin/TI (10 anos ~ efetivamente sem expirar).
SESSAO_ADMIN_SEGUNDOS = 60 * 60 * 24 * 365 * 10


@receiver(user_logged_in)
def definir_janela_de_acesso(sender, request, user, **kwargs):
    """
    Define a expiração da sessão no login:

    - Admin/TI (is_staff): sessão longa (ilimitada na prática) — não sofre a
      janela de 1 minuto nem mostra o contador na tela.
    - Demais usuários (operacional): janela de acesso ABSOLUTA de
      SESSION_COOKIE_AGE segundos, contada do login e sem renovar por atividade.
    """
    if request is None:
        return

    if user.is_staff:
        request.session.set_expiry(SESSAO_ADMIN_SEGUNDOS)
        request.session['expira_epoch'] = 0  # sinaliza "sem contador"
        return

    request.session['expira_epoch'] = int(time.time()) + settings.SESSION_COOKIE_AGE
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
