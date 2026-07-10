from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission, User

from .models import LogTrigger

# Permissões próprias do app — as únicas que fazem sentido atribuir aqui.
_PERMISSOES_APP = ('pode_operar_trava', 'pode_ver_logs')


def _queryset_permissoes_app():
    """Só as permissões do app 'core' (esconde as ~40 internas do Django)."""
    return Permission.objects.filter(
        codename__in=_PERMISSOES_APP,
        content_type__app_label='core',
    )


class GrupoAdmin(GroupAdmin):
    """Ao editar um grupo, mostra apenas as permissões do app."""

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'permissions':
            kwargs['queryset'] = _queryset_permissoes_app()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class UsuarioAdmin(UserAdmin):
    """Ao editar um usuário, mostra apenas as permissões do app."""

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'user_permissions':
            kwargs['queryset'] = _queryset_permissoes_app()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# Substitui os admins padrão de Grupo e Usuário pelos enxutos.
admin.site.unregister(Group)
admin.site.unregister(User)
admin.site.register(Group, GrupoAdmin)
admin.site.register(User, UsuarioAdmin)


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
