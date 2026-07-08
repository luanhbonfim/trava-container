from django.contrib import admin

from .models import LogTrigger


@admin.register(LogTrigger)
class LogTriggerAdmin(admin.ModelAdmin):
    list_display = (
        'criado_em', 'get_acao_display', 'nome_informado', 'motivo',
        'usuario', 'status_anterior', 'status_final', 'sucesso', 'ip',
    )
    list_filter = ('acao', 'sucesso', 'criado_em')
    search_fields = ('nome_informado', 'motivo', 'usuario__username', 'mensagem')
    date_hierarchy = 'criado_em'
    readonly_fields = (
        'criado_em', 'usuario', 'nome_informado', 'motivo', 'acao',
        'status_anterior', 'status_final', 'sucesso', 'mensagem', 'ip',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Log de auditoria não pode ser apagado (integridade do histórico).
        return False
