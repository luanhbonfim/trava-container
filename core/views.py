import ipaddress
import logging
import socket
import subprocess

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import LogTrigger
from .services import oracle

logger = logging.getLogger(__name__)


def _ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _hostname_dns(ip):
    """Nome via DNS reverso (PTR). '' se não resolver."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ''


def _hostname_netbios(ip):
    """
    Nome da máquina via NetBIOS (rede Windows), usando `nmblookup -A <ip>`.
    Funciona mesmo sem DNS reverso. Requer o pacote samba-common-bin.
    Retorna '' se o utilitário não existir ou não achar o nome.
    """
    try:
        saida = subprocess.run(
            ['nmblookup', '-A', ip],
            capture_output=True, text=True, timeout=3,
        ).stdout
    except Exception:
        return ''
    # A linha do nome da estação é a que tem <00> e NÃO é <GROUP>.
    for linha in saida.splitlines():
        if '<00>' in linha and '<GROUP>' not in linha:
            nome = linha.split()[0].strip()
            if nome:
                return nome
    return ''


def _hostname(ip):
    """
    Resolve o hostname da máquina de origem. Prioriza NetBIOS (rede Windows)
    e usa DNS reverso como reserva. Retorna '' se nada resolver.
    """
    if not ip:
        return ''
    try:
        ipaddress.ip_address(ip)  # valida antes de chamar processo externo
    except ValueError:
        return ''
    return _hostname_netbios(ip) or _hostname_dns(ip)


def _consultar_status():
    """Retorna (status, erro). status é 'ENABLED'/'DISABLED' ou None se erro."""
    try:
        return oracle.status_trigger(), None
    except Exception as exc:  # OracleConfigError, TriggerNaoEncontrada, DB error
        return None, str(exc)


@login_required
def painel(request):
    status, erro = _consultar_status()
    if erro:
        # O detalhe técnico (nome da trigger, ORA-..., etc.) fica só no log
        # do servidor; ao usuário mostra-se apenas uma mensagem genérica.
        logger.warning('Falha ao consultar status da trava: %s', erro)
    contexto = {
        'status': status,
        'erro': bool(erro),
        'nome_sugerido': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'core/painel.html', contexto)


@login_required
@permission_required('core.pode_operar_trava', raise_exception=True)
@require_POST
def alternar(request):
    """Ativa/desativa a trigger. Exige o nome de quem está executando."""
    nome_informado = (request.POST.get('nome_informado') or '').strip()
    motivo = (request.POST.get('motivo') or '').strip()

    if not nome_informado or not motivo:
        messages.error(request, 'Informe o nome e o motivo para executar a ação.')
        return redirect('painel')

    status_atual, erro = _consultar_status()
    if erro:
        messages.error(request, 'Não foi possível falar com o sistema. Chame a TI.')
        return redirect('painel')

    ip = _ip(request)

    # Decide a ação a partir de UMA única leitura de status e executa
    # diretamente a operação correspondente — assim o log reflete
    # exatamente o que foi feito (sem reler o status no meio).
    if status_atual == 'ENABLED':
        acao = LogTrigger.ACAO_DESATIVAR
        operacao = oracle.desativar_trigger
    else:
        acao = LogTrigger.ACAO_ATIVAR
        operacao = oracle.ativar_trigger

    log = LogTrigger(
        usuario=request.user,
        nome_informado=nome_informado,
        motivo=motivo,
        acao=acao,
        status_anterior=status_atual or '',
        ip=ip,
        hostname=_hostname(ip),
    )

    try:
        novo_status, msg = operacao()
        log.status_final = novo_status
        log.sucesso = True
        log.mensagem = msg
        log.save()
        messages.success(request, msg)
    except Exception as exc:
        log.status_final = status_atual or ''
        log.sucesso = False
        log.mensagem = str(exc)
        log.save()
        messages.error(request, 'Não foi possível concluir a operação. Chame a TI.')

    return redirect('painel')


@login_required
@permission_required('core.pode_ver_logs', raise_exception=True)
def logs(request):
    registros = LogTrigger.objects.select_related('usuario').all()[:500]
    return render(request, 'core/logs.html', {'registros': registros})
