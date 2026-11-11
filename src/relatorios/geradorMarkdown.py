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


def numerosEtapasRealizadas(resultadoApuracao: dict[str, Any]) -> list[int]:
    """Números das etapas presentes na apuração, em ordem (só as realizadas; sem 4 etapas fixas)."""
    return sorted(int(e["numeroEtapa"]) for e in resultadoApuracao["etapas"])


DESCRICAO_DESEMPATE_INDIVIDUAL = {
    "ultimoPercurso": "o último percurso e os percursos anteriores",
    "primeirosLugares": "o número de 1ºs, 2ºs lugares etc. e o último confronto direto",
}


def formatarCelulaEtapa(des: DesempenhoEtapaCalculado) -> str:
    """Formata o resultado de uma etapa na tabela individual."""
    if not des.inscrito and not des.atuouComoVoluntario and not des.ajustadoOficial:
        base = "0,00 (-)"
    elif des.atuouComoVoluntario:
        base = f"*{formatarMoedaPontos(des.pontosFinais)}*"
    elif des.colocacao is not None:
        base = f"{formatarMoedaPontos(des.pontosFinais)} ({des.colocacao}º)"
    else:
        base = f"{formatarMoedaPontos(des.pontosFinais)} ({des.statusSigla})"

    if des.ajustadoOficial:
        base += "†"
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
    regras = resultadoApuracao["regras"]
    numeros = numerosEtapasRealizadas(resultadoApuracao)

    linhas: list[str] = [
        f"# Resultado de Clubes — {edicao} ({ano})",
        "",
        f"Apuração calculada conforme o **{regras.artigos.clubes}** do {regras.nomeRegulamento} "
        "(soma dos pontos dos 3 atletas filiados à CBO melhores classificados em cada categoria, por etapa).",
        "",
        "## Classificação Geral de Clubes",
        "",
        "| Class. | Clube | Federação | Atletas | " + " | ".join(f"{n}ª Etapa" for n in numeros) + " | Total Pontos |",
        "| :---: | :--- | :---: | :---: | " + " ".join("---: |" for _ in numeros) + " ---: |",
    ]

    for idx, c in enumerate(clubes, start=1):
        colocStr = f"**{idx}º**" if idx <= 3 else f"{idx}º"
        nomeClube = f"**{c['sigla']}** ({c['nome']})" if idx <= 3 else f"{c['sigla']} ({c['nome']})"
        fed = c.get("federacaoSigla") or "-"
        pontosEtapas = " | ".join(
            formatarMoedaPontos(c["pontosPorEtapa"].get(et, Decimal('0.00'))) for et in numeros
        )
        tot = formatarMoedaPontos(c["totalPontos"])
        if idx <= 3:
            tot = f"**{tot}**"
        linhas.append(
            f"| {colocStr} | {nomeClube} | {fed} | {c['qtdAtletas']} | {pontosEtapas} | {tot} |"
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
    regras = resultadoApuracao["regras"]
    art = regras.artigos
    numeros = numerosEtapasRealizadas(resultadoApuracao)
    nEt = len(numeros)
    minimo = resultadoApuracao["minimoMetadeEtapas"]

    if resultadoApuracao["descarteAplicado"]:
        linhaDescarte = (
            f"- **Descarte obrigatório ({art.descarte}):** 1 etapa de menor pontuação descartada, indicada com "
            f"valores tachados (ex.: `~~35,00 (3º)~~`) (campeonato com {nEt} etapas)."
        )
    elif regras.temDescarte:
        linhaDescarte = (
            f"- **Sem descarte ({art.descarte}):** campeonato com {nEt} etapas realizadas "
            f"(o descarte exige mais de {regras.etapasRealizadasParaDescarte}); vale o somatório de todas."
        )
    else:
        linhaDescarte = (
            f"- **Sem descarte ({art.classificacaoGeral}):** o regulamento de {regras.ano} classifica pelo "
            "somatório dos pontos de todas as etapas."
        )

    linhas: list[str] = [
        f"# Classificação Individual — {edicao} ({ano})",
        "",
        f"Apuração calculada conforme o {regras.nomeRegulamento} "
        f"(pontuação: **{art.pontuacao}**; troca de categoria: **{art.trocaCategoria}**; "
        f"classificação geral: **{art.classificacaoGeral}**):",
        linhaDescarte,
        f"- **Voluntários e Árbitros ({art.voluntariosMinimo}):** atribuição de pontuação média na etapa de atuação, "
        "indicada com valores em itálico (ex.: `*20,00*`).",
        f"- **Elegibilidade à premiação final ({art.premiacao}):** filiado à CBO e com participação em no mínimo "
        f"metade das etapas realizadas (mínimo de {minimo} etapas).",
    ]
    nAjustes = len(resultadoApuracao.get("ajustesOficiais", []))
    nPosicoes = len(resultadoApuracao.get("posicoesOficiais", []))
    nOmissoes = len(resultadoApuracao.get("omissoesOficiais", []))
    if nAjustes or nPosicoes or nOmissoes:
        linhas.append(
            f"- **Resultado oficial publicado (ADR-007):** o publicado pela FECORI prevalece sobre o recálculo; "
            f"{nAjustes} notas (marcadas com †), {nPosicoes} posições e {nOmissoes} atletas fora da lista foram "
            "mantidos como publicados."
        )
    linhas.append("")

    cabecalhoEtapas = " | ".join(f"{n}ª Etapa" for n in numeros)
    alinhamentoEtapas = " ".join(":---: |" for _ in numeros)
    for categoria in sorted(fichasPorCat.keys()):
        if ehCategoriaSemPontuacao(categoria):
            continue
        fichas = fichasPorCat[categoria]
        linhas.extend([
            f"## Categoria: {categoria}",
            "",
            f"| Col. | CBO | Atleta | Clube | {cabecalhoEtapas} | Total | Premiação ({art.premiacao}) |",
            f"| :---: | :---: | :--- | :---: | {alinhamentoEtapas} ---: | :---: |",
        ])
        for f in fichas:
            colStr = f"**{f.colocacaoFinal}º**" if 1 <= f.colocacaoFinal <= 3 else (f"{f.colocacaoFinal}º" if f.colocacaoFinal > 0 else "-")
            if not f.categoriaValidaFinal:
                colStr = f"*({art.trocaCategoria})*"
            celulasEtapas = " | ".join(formatarCelulaEtapa(f.etapas[et]) for et in numeros)
            totStr = f"**{formatarMoedaPontos(f.pontuacaoTotal)}**" if 1 <= f.colocacaoFinal <= 3 else formatarMoedaPontos(f.pontuacaoTotal)
            premStr = "Sim" if f.elegivelPremiacao else f"Não ({f.etapasParticipadas}/{nEt})"
            linhas.append(
                f"| {colStr} | {f.cbo} | {f.nome} | {f.clubeSigla} | {celulasEtapas} | {totStr} | {premStr} |"
            )
        empatados = [f for f in fichas if f.empateNaoResolvido]
        if empatados:
            cbos = ", ".join(str(f.cbo) for f in empatados)
            criterio = DESCRICAO_DESEMPATE_INDIVIDUAL[regras.desempateIndividual]
            linhas.extend([
                "",
                f"> **Empate não resolvido ({art.desempateIndividual}):** CBO {cbos} seguem empatados após {criterio}; "
                "o critério de maior idade não é aplicado automaticamente e deve ser decidido pelo apurador.",
            ])
        linhas.append("")

    return "\n".join(linhas) + "\n"
