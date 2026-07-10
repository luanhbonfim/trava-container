import time


def sessao(request):
    """
    Expõe aos templates quantos segundos faltam para a janela de acesso
    expirar (contagem absoluta desde o login).

    Retorna None (sem contador) para usuários não autenticados e para
    admin/TI (is_staff), que têm sessão longa.
    """
    restante = None
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and not user.is_staff:
        deadline = request.session.get('expira_epoch')
        if deadline:
            restante = max(0, int(deadline) - int(time.time()))
    return {'sessao_restante': restante}
