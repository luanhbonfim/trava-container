import time


def sessao(request):
    """
    Expõe aos templates quantos segundos faltam para a janela de acesso
    expirar (contagem absoluta desde o login). Retorna None quando o
    usuário não está autenticado.
    """
    restante = None
    if request.user.is_authenticated:
        deadline = request.session.get('expira_epoch')
        if deadline:
            restante = max(0, int(deadline) - int(time.time()))
        else:
            # Fallback: sessão criada sem o instante-limite (ex.: antes deste
            # recurso). Usa o tempo padrão de expiração da sessão.
            try:
                restante = request.session.get_expiry_age()
            except Exception:
                restante = None
    return {'sessao_restante': restante}
