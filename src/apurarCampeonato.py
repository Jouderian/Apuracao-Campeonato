#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ponto de entrada (CLI) para execução da apuração do campeonato."""
import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.extracaoAccess.leitorVoluntarios import lerVoluntariosMarkdown
from src.motorCalculo.pontuacao import apurarCampeonatoCCO
from src.relatorios.geradorMarkdown import (
    gerarRelatorioClubesMarkdown,
    gerarRelatorioIndividualMarkdown,
)


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

    pastaAno = os.path.join(RAIZ, 'Dados', str(args.ano))
    arqEtapas = os.path.join(pastaAno, 'extraidos', f'etapasHelga{args.ano}.json')
    arqVoluntariosMd = os.path.join(pastaAno, 'entradas', f'voluntarios{args.competicao}.md')

    if not os.path.isfile(arqEtapas):
        print(f"Arquivo extraído não encontrado: {arqEtapas}", file=sys.stderr)
        return 1

    with open(arqEtapas, encoding='utf-8') as fh:
        dadosHelga = json.load(fh)

    if os.path.isfile(arqVoluntariosMd):
        with open(arqVoluntariosMd, encoding='utf-8') as fh:
            dadosVoluntarios = lerVoluntariosMarkdown(fh.read())
    else:
        dadosVoluntarios = {"voluntarios": [], "penalidadesArt23": []}

    resultado = apurarCampeonatoCCO(dadosHelga, dadosVoluntarios)

    edicao = f"XX {args.competicao}" if args.ano == 2026 else f"{args.competicao} {args.ano}"
    pastaResultados = os.path.join(pastaAno, 'resultados')
    os.makedirs(pastaResultados, exist_ok=True)

    arqClubesMd = os.path.join(pastaResultados, f'resultadoClubes{args.competicao}.md')
    arqIndivMd = os.path.join(pastaResultados, f'resultadoIndividual{args.competicao}.md')

    with open(arqClubesMd, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(gerarRelatorioClubesMarkdown(args.ano, edicao, resultado))

    with open(arqIndivMd, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(gerarRelatorioIndividualMarkdown(args.ano, edicao, resultado))

    print(f"Apuração do {edicao} ({args.ano}) concluída:")
    print(f"  - Voluntários lidos ({len(dadosVoluntarios['voluntarios'])}): {os.path.relpath(arqVoluntariosMd, RAIZ)}")
    print(f"  - Clubes:     {os.path.relpath(arqClubesMd, RAIZ)}")
    print(f"  - Individual: {os.path.relpath(arqIndivMd, RAIZ)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
