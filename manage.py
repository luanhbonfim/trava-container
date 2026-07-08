#!/usr/bin/env python
"""Utilitário de linha de comando do Django para o projeto PESO_CONTAINER."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'peso_container.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Ele está instalado e "
            "disponível na sua variável PYTHONPATH? Você esqueceu de "
            "ativar um ambiente virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
