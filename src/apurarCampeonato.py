#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ponto de entrada (CLI) para execução da apuração do campeonato."""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calcula o resultado individual e por clubes do Campeonato Cearense de Orientação (CCO/CCOS)."
    )
    parser.add_argument('--ano', type=int, default=2026, help="Ano da edição do campeonato (ex.: 2026)")
    parser.add_argument(
        '--competicao',
        choices=['CCO', 'CCOS'],
        default='CCO',
        help="Competição a apurar (CCO ou CCOS)",
    )
    args = parser.parse_args()
    print(f"Apuração configurada para {args.competicao} {args.ano}. Aguardando ingestão das etapas em Dados/{args.ano}/entradas/.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

