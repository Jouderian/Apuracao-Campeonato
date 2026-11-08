# -*- coding: utf-8 -*-
"""Geração de relatórios em Markdown para os resultados individuais e por clubes."""
from decimal import Decimal
from typing import Any

from src.motorCalculo.pontuacao import (
    ClassificacaoAtletaCategoria,
    DesempenhoEtapaCalculado,
    ehCategoriaSemPontuacao,
)


def formatarMoedaPontos(valor: Decimal) -> str:
    """Formata um Decimal no padrão brasileiro (ex.: 6.853,33 ou 40,00)."""
    quant = f"{valor:,.2f}"
    return quant.replace(",", "X").replace(".", ",").replace("X", ".")


def formatarCelulaEtapa(des: DesempenhoEtapaCalculado) -> str:
    """Formata o resultado de uma etapa na tabela individual."""
    if not des.inscrito and not des.atuouComoVoluntario:
        base = "0,00 (-)"
    elif des.atuouComoVoluntario:
        base = f"{formatarMoedaPontos(des.pontosFinais)} (VOL)"
    elif des.colocacao is not None:
        base = f"{formatarMoedaPontos(des.pontosFinais)} ({des.colocacao}º)"
    else:
        base = f"{formatarMoedaPontos(des.pontosFinais)} ({des.statusSigla})"

    if des.descartada:
        return f"~~{base}~~"
    return base


def gerarRelatorioClubesMarkdown(
    ano: int,
    edicao: str,
    resultadoApuracao: dict[str, Any],
) -> str:
    """Gera o relatório Markdown da classificação geral e por etapa dos clubes."""
    etapas = resultadoApuracao["etapas"]
    clubes = resultadoApuracao["classificacaoClubes"]

    linhas: list[str] = [
        f"# Resultado de Clubes — {edicao} ({ano})",
        "",
        "Apuração calculada conforme o **Art. 35** do Regulamento das Competições Cearenses de Orientação de 2026 (soma dos pontos dos 3 atletas filiados à CBO melhores classificados em cada categoria, por etapa).",
        "",
        "## Classificação Geral de Clubes",
        "",
        "| Class. | Clube | Federação | Atletas | 1ª Etapa | 2ª Etapa | 3ª Etapa | 4ª Etapa | Total Pontos |",
        "| :---: | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for idx, c in enumerate(clubes, start=1):
        colocStr = f"**{idx}º**" if idx <= 3 else f"{idx}º"
        nomeClube = f"**{c['sigla']}** ({c['nome']})" if idx <= 3 else f"{c['sigla']} ({c['nome']})"
        fed = c.get("federacaoSigla") or "-"
        p1 = formatarMoedaPontos(c["pontosPorEtapa"].get(1, Decimal('0.00')))
        p2 = formatarMoedaPontos(c["pontosPorEtapa"].get(2, Decimal('0.00')))
        p3 = formatarMoedaPontos(c["pontosPorEtapa"].get(3, Decimal('0.00')))
        p4 = formatarMoedaPontos(c["pontosPorEtapa"].get(4, Decimal('0.00')))
        tot = formatarMoedaPontos(c["totalPontos"])
        if idx <= 3:
            tot = f"**{tot}**"
        linhas.append(
            f"| {colocStr} | {nomeClube} | {fed} | {c['qtdAtletas']} | {p1} | {p2} | {p3} | {p4} | {tot} |"
        )

    linhas.extend([
        "",
        "## Resumo das Etapas Apuradas",
        "",
        "| Etapa | Data | Local | Clube Organizador |",
        "| :---: | :---: | :--- | :--- |",
    ])
    for e in etapas:
        linhas.append(
            f"| {e['numeroEtapa']}ª | {e['data']} | {e['local']} | {e['clubeOrganizadorSigla']} |"
        )

    return "\n".join(linhas) + "\n"


def gerarRelatorioIndividualMarkdown(
    ano: int,
    edicao: str,
    resultadoApuracao: dict[str, Any],
) -> str:
    """Gera o relatório Markdown da classificação individual por categoria."""
    fichasPorCat: dict[str, list[ClassificacaoAtletaCategoria]] = resultadoApuracao["fichasPorCategoria"]

    linhas: list[str] = [
        f"# Classificação Individual — {edicao} ({ano})",
        "",
        "Apuração calculada conforme os **Arts. 31 a 34 e 39** do Regulamento das Competições Cearenses de Orientação de 2026:",
        "- **Descarte obrigatório (Art. 34):** 1 etapa de menor pontuação marcada como `~~riscada~~` (campeonato com 4 etapas).",
        "- **Voluntários/Árbitros (Art. 33, § 1º):** identificados com `(VOL)` na etapa de atuação.",
        "- **Elegibilidade à premiação final (Art. 39, § 1º):** filiado à CBO e com participação em no mínimo metade das etapas realizadas (mínimo de 2 etapas).",
        "",
    ]

    for categoria in sorted(fichasPorCat.keys()):
        if ehCategoriaSemPontuacao(categoria):
            continue
        fichas = fichasPorCat[categoria]
        linhas.extend([
            f"## Categoria: {categoria}",
            "",
            "| Col. | CBO | Atleta | Clube | 1ª Etapa | 2ª Etapa | 3ª Etapa | 4ª Etapa | Total | Premiação (Art. 39) |",
            "| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | ---: | :---: |",
        ])
        for f in fichas:
            colStr = f"**{f.colocacaoFinal}º**" if 1 <= f.colocacaoFinal <= 3 else (f"{f.colocacaoFinal}º" if f.colocacaoFinal > 0 else "-")
            if not f.categoriaValidaFinal:
                colStr = "*(Art. 32)*"
            e1 = formatarCelulaEtapa(f.etapas[1])
            e2 = formatarCelulaEtapa(f.etapas[2])
            e3 = formatarCelulaEtapa(f.etapas[3])
            e4 = formatarCelulaEtapa(f.etapas[4])
            totStr = f"**{formatarMoedaPontos(f.pontuacaoTotal)}**" if 1 <= f.colocacaoFinal <= 3 else formatarMoedaPontos(f.pontuacaoTotal)
            premStr = "Sim" if f.elegivelPremiacao else f"Não ({f.etapasParticipadas}/4)"
            linhas.append(
                f"| {colStr} | {f.cbo} | {f.nome} | {f.clubeSigla} | {e1} | {e2} | {e3} | {e4} | {totStr} | {premStr} |"
            )
        linhas.append("")

    return "\n".join(linhas) + "\n"

