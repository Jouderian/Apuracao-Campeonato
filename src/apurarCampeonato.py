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
from src.extracaoAccess.validarEntrada import conferirHashNoManifesto, validarDadosHelga
from src.motorCalculo.pontuacao import apurarCampeonatoCCO
from src.relatorios.geradorExcelPdf import (
    gerarPdfResultadoClubes,
    gerarPdfResultadoParcialAtletas,
    gerarPlanilhaExcelApuracao,
)
from src.relatorios.geradorMarkdown import (
    gerarRelatorioClubesMarkdown,
    gerarRelatorioIndividualMarkdown,
)


def localizarLogoEdicao(ano: int, competicao: str) -> str | None:
    """Localiza a logo oficial da edição em Dados/<ano>/ ou no repositório Regulamentos-de-Orientacao."""
    candidatos = [
        os.path.join(RAIZ, "Dados", str(ano), f"logo{competicao}.jpeg"),
        os.path.join(RAIZ, "Dados", str(ano), f"logo{competicao}.png"),
        os.path.join(RAIZ, "Dados", str(ano), f"logo{competicao}.jpg"),
        os.path.join(
            os.path.dirname(RAIZ),
            "Regulamentos-de-Orientacao",
            "Documentos",
            str(ano),
            f"logo{competicao}.jpeg",
        ),
        os.path.join(
            os.path.dirname(RAIZ),
            "Regulamentos-de-Orientacao",
            "Documentos",
            str(ano),
            f"logo{competicao}.png",
        ),
    ]
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


ANO_EDICAO_ZERO = 2006   # 2026 = XX edição (ano - 2006)


def converterParaRomano(numero: int) -> str:
    """Converte um inteiro positivo (1 a 3999) em numeral romano."""
    if not 0 < numero < 4000:
        raise ValueError(f"Número fora do intervalo romano (1 a 3999): {numero}")
    simbolos = (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    )
    partes = []
    for valor, simbolo in simbolos:
        quantidade, numero = divmod(numero, valor)
        partes.append(simbolo * quantidade)
    return "".join(partes)


def obterEdicaoRomana(ano: int) -> str:
    """Retorna o numeral romano da edição do CCO a partir do ano (2025 = XIX, 2026 = XX, etc.)."""
    return converterParaRomano(ano - ANO_EDICAO_ZERO)


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
    parser.add_argument(
        '--oficial',
        action='store_true',
        help="Gera os PDFs finais (resultadoIndividual e resultadoClubes) após conclusão da revisão pela FECORI",
    )
    args = parser.parse_args()

    pastaAno = os.path.join(RAIZ, 'Dados', str(args.ano))
    arqEtapas = os.path.join(pastaAno, 'extraidos', f'etapasHelga{args.ano}.json')
    arqVoluntariosMd = os.path.join(pastaAno, 'entradas', f'voluntarios{args.competicao}.md')

    if not os.path.isfile(arqEtapas):
        print(f"Arquivo extraído não encontrado: {arqEtapas}", file=sys.stderr)
        return 1

    try:
        with open(arqEtapas, encoding='utf-8') as fh:
            dadosHelga = json.load(fh)
        validarDadosHelga(dadosHelga)
        conferirHashNoManifesto(dadosHelga, args.ano, os.path.join(RAIZ, 'Dados'))
    except (ValueError, OSError) as erro:
        print(f"Entrada recusada ({arqEtapas}): {erro}", file=sys.stderr)
        return 1

    if os.path.isfile(arqVoluntariosMd):
        with open(arqVoluntariosMd, encoding='utf-8') as fh:
            dadosVoluntarios = lerVoluntariosMarkdown(fh.read())
    else:
        dadosVoluntarios = {"voluntarios": [], "penalidadesArt23": []}

    resultado = apurarCampeonatoCCO(dadosHelga, dadosVoluntarios)

    edicaoRomanos = obterEdicaoRomana(args.ano)
    edicao = f"{edicaoRomanos} {args.competicao}"
    pastaResultados = os.path.join(pastaAno, 'resultados')
    os.makedirs(pastaResultados, exist_ok=True)

    caminhoLogo = localizarLogoEdicao(args.ano, args.competicao)

    arqClubesMd = os.path.join(pastaResultados, f'resultadoClubes{args.competicao}.md')
    arqIndivMd = os.path.join(pastaResultados, f'resultadoIndividual{args.competicao}.md')
    nomePlanilha = f'apuracaoCampeonato{args.ano}.xlsx'
    arqXlsx = os.path.join(pastaResultados, nomePlanilha)
    arqParcialPdf = os.path.join(pastaResultados, f'resultadoParcial{args.competicao}.pdf')
    arqIndivPdf = os.path.join(pastaResultados, f'resultadoIndividual{args.competicao}.pdf')
    arqClubesPdf = os.path.join(pastaResultados, f'resultadoClubes{args.competicao}.pdf')

    if args.oficial:
        with open(arqClubesMd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(gerarRelatorioClubesMarkdown(args.ano, edicao, resultado))

    with open(arqIndivMd, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(gerarRelatorioIndividualMarkdown(args.ano, edicao, resultado))

    gerarPlanilhaExcelApuracao(args.ano, edicao, edicaoRomanos, resultado, arqXlsx)
    # O resultado parcial não é oficial e por isso nunca leva a logo da edição.
    gerarPdfResultadoParcialAtletas(
        args.ano,
        edicaoRomanos,
        resultado,
        [arqParcialPdf],
        caminhoLogo=None,
    )
    if args.oficial:
        gerarPdfResultadoParcialAtletas(
            args.ano,
            edicaoRomanos,
            resultado,
            [arqIndivPdf],
            caminhoLogo=caminhoLogo,
        )
        gerarPdfResultadoClubes(
            args.ano,
            edicaoRomanos,
            resultado,
            arqClubesPdf,
            nomePlanilha,
            caminhoLogo=caminhoLogo,
        )

    empatados = sorted(
        {(f.categoria, f.cbo) for lista in resultado["fichasPorCategoria"].values() for f in lista if f.empateNaoResolvido}
    )
    if empatados:
        print(
            "ATENÇÃO: empate não resolvido (Art. 34, § 2º; critério de idade não aplicado, ADR-003) em: "
            + ", ".join(f"{cat} CBO {cbo}" for cat, cbo in empatados),
            file=sys.stderr,
        )
    print(f"Apuração do {edicao} ({args.ano}) concluída:")
    print(f"  - Voluntários lidos ({len(dadosVoluntarios['voluntarios'])}): {os.path.relpath(arqVoluntariosMd, RAIZ)}")
    if caminhoLogo:
        print(f"  - Logo da edição:   {os.path.relpath(caminhoLogo, RAIZ)}")
    print(f"  - Parcial (PDF):    {os.path.relpath(arqParcialPdf, RAIZ)}")
    if args.oficial:
        print(f"  - Individual (PDF): {os.path.relpath(arqIndivPdf, RAIZ)}")
        print(f"  - Clubes (PDF):     {os.path.relpath(arqClubesPdf, RAIZ)}")
    print(f"  - Planilha (XLSX):  {os.path.relpath(arqXlsx, RAIZ)}")
    print(f"  - Individual (MD):  {os.path.relpath(arqIndivMd, RAIZ)}")
    if args.oficial:
        print(f"  - Clubes (MD):      {os.path.relpath(arqClubesMd, RAIZ)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
