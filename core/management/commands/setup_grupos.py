"""
Cria/atualiza os grupos de acesso e suas permissões.

Rode após o migrate:
    python manage.py setup_grupos

Grupos:
  - Operadores : pode travar/destravar (não vê os logs)
  - Auditoria  : pode ver os logs (não opera a trava)
  - Gestores   : opera a trava E vê os logs

Superusuário tem acesso a tudo automaticamente (não precisa de grupo).
Depois, associe cada usuário a um grupo em /admin/.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

GRUPOS = {
    'Operadores': ['pode_operar_trava'],
    'Auditoria':  ['pode_ver_logs'],
    'Gestores':   ['pode_operar_trava', 'pode_ver_logs'],
}


class Command(BaseCommand):
    help = 'Cria/atualiza os grupos de acesso e suas permissões.'

    def handle(self, *args, **options):
        for nome, codenames in GRUPOS.items():
            grupo, criado = Group.objects.get_or_create(name=nome)
            perms = list(
                Permission.objects.filter(
                    codename__in=codenames,
                    content_type__app_label='core',
                )
            )
            faltando = set(codenames) - {p.codename for p in perms}
            if faltando:
                self.stderr.write(self.style.ERROR(
                    f'Permissões não encontradas: {", ".join(faltando)}. '
                    'Rode "python manage.py migrate" antes.'
                ))
                continue
            grupo.permissions.set(perms)
            estado = 'criado' if criado else 'atualizado'
            self.stdout.write(self.style.SUCCESS(
                f'Grupo "{nome}" {estado} -> {", ".join(codenames)}'
            ))
        self.stdout.write(self.style.SUCCESS('Grupos configurados.'))
