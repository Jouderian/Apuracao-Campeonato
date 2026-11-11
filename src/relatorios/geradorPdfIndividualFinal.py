# -*- coding: utf-8 -*-
"""PDF do Resultado Individual final, no layout publicado pela FECORI (A4 paisagem).

Uma linha por atleta e categoria, categorias na ordem da FECORI e mantidas inteiras na página, pontos por etapa
com destaque (amarelo = média de voluntário/árbitro, laranja claro = não classificado com 1 ponto), coluna de
Premiação (troféu, medalhas ou "Art.42 §…" para quem não cumpriu a participação mínima) e, na última página, a
linha de totais, o quadro de premiação e a legenda. O parcial (não oficial) usa outro layout, em geradorExcelPdf.
"""
import os
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.motorCalculo.pontuacao import (
    ClassificacaoAtletaCategoria,
    DesempenhoEtapaCalculado,
    arredondarPontuacao,
    ehCategoriaSemPontuacao,
)
from src.relatorios.geradorExcelPdf import (
    _contarInscricoesPorEtapa,
    _inserirTextoAlinhado,
    _obterMapaFontesPdf,
    carregarBytesLogoSemFundo,
)
from src.relatorios.geradorMarkdown import numerosEtapasRealizadas

Cor = tuple[float, float, float]
Fonte = tuple[str, str | None, Any]

# Ordem das categorias no resultado da FECORI (elite, VIP, veteranos, sêniores, masters, adulto, juvenis, infantis).
ORDEM_CATEGORIAS: tuple[str, ...] = (
    "D Adulto E", "H Adulto E", "D Junior E", "H Junior E", "H VIP A", "D VIP B", "H VIP B",
    "H Vet A", "D Vet B", "H Vet B", "D Vet N", "H Vet N",
    "D Sênior A", "H Sênior A", "D Sênior B", "H Sênior B", "D Sênior N", "H Sênior N",
    "D Master A", "H Master A", "D Master B", "H Master B", "D Master N", "H Master N",
    "D Adulto A", "H Adulto A", "D Adulto B", "H Adulto B", "D Adulto N", "H Adulto N",
    "H Junior A", "D Junior B", "H Junior B", "D Junior N", "H Junior N",
    "H Juven A", "D Juven B", "H Juven B", "D Juven N", "H Juven N",
    "D Infant B", "H Infant B", "H Infant N",
)

# Geometria (pt) medida no PDF de referência da FECORI (A4 paisagem).
LARGURA, ALTURA = 841.92, 595.32
X_ESQ, X_DIR = 14.0, 832.0
ALT_CABECALHO, ALT_LINHA = 19.5, 18.4
Y_CAB_PRIMEIRA, Y_CAB_DEMAIS = 105.0, 29.0
Y_LIMITE_LINHAS = 551.0
X_CATEGORIA, X_CLASS_CENTRO, X_CBO_DIR, X_ATLETA, X_CLUBE = 16.0, 105.6, 169.7, 173.6, 411.0
X_TOTAL_DIR = 755.8
X_ETAPA_DIR_ULTIMA, PASSO_ETAPA = 705.3, 55.27
X_PREMIO = (758.0, 817.0)
Y_RODAPE = 578.0

AZUL: Cor = (0.267, 0.447, 0.769)
AZUL_CLARO: Cor = (0.851, 0.882, 0.949)
CINZA: Cor = (0.851, 0.851, 0.851)
CINZA_ESCURO: Cor = (0.498, 0.498, 0.498)
CINZA_TRACO: Cor = (0.35, 0.35, 0.35)
CINZA_LEGENDA: Cor = (0.682, 0.667, 0.667)
AMARELO: Cor = (1.0, 1.0, 0.0)
LARANJA_CLARO: Cor = (1.0, 0.949, 0.8)
LARANJA: Cor = (1.0, 0.753, 0.0)
BRONZE: Cor = (0.929, 0.49, 0.192)
OURO: Cor = (1.0, 0.851, 0.4)
VERMELHO: Cor = (1.0, 0.0, 0.0)
PRETO: Cor = (0.0, 0.0, 0.0)
BRANCO: Cor = (1.0, 1.0, 1.0)

PREMIO_TROFEU, PREMIO_OURO, PREMIO_PRATA, PREMIO_BRONZE, PREMIO_ART42 = "trofeu", "ouro", "prata", "bronze", "art42"


def ordenarCategorias(categorias: list[str]) -> list[str]:
    """Ordena as categorias como no resultado da FECORI; as não previstas vão ao fim, em ordem alfabética."""
    conhecidas = [c for c in ORDEM_CATEGORIAS if c in categorias]
    return conhecidas + sorted(c for c in categorias if c not in ORDEM_CATEGORIAS)


def rotuloArtigo(artigo: str) -> str:
    """Abrevia a citação do artigo para a legenda: `Art. 42, § 1º` vira `Art.42 §1°`; só o artigo vira `Art.20`."""
    m = re.match(r"Art\. (\d+)(?:, § (\d+)º)?", artigo)
    if not m:
        return artigo
    return f"Art.{m.group(1)}" + (f" §{m.group(2)}°" if m.group(2) else "")


def classificarPremio(ficha: ClassificacaoAtletaCategoria) -> str | None:
    """Premiação do atleta: troféu (campeão), ouro (campeão de categoria Novato), prata, bronze ou Art.42.

    Medalha: colocação final de 1º a 3º com participação mínima e filiação. O rótulo do Art.42 (participação
    mínima) segue a posição na categoria, como no resultado publicado: quem está entre os 3 primeiros com pontos,
    mas não tem direito à premiação, inclusive na categoria que perde pela troca de categoria (Art. 35).
    """
    if 1 <= ficha.colocacaoFinal <= 3 and ficha.elegivelPremiacao:
        if ficha.colocacaoFinal == 1:
            return PREMIO_OURO if ficha.categoria.endswith(" N") else PREMIO_TROFEU
        return PREMIO_PRATA if ficha.colocacaoFinal == 2 else PREMIO_BRONZE
    if 1 <= ficha.colocacaoNaCategoria <= 3 and ficha.pontuacaoTotal > 0:
        return PREMIO_ART42
    return None


def formatarPontos(valor: Decimal) -> str:
    """Formata pontos com 2 casas e vírgula decimal (ex.: 22,33)."""
    return f"{arredondarPontuacao(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estiloDaCelula(des: DesempenhoEtapaCalculado) -> tuple[str, str]:
    """Texto e estilo da célula de uma etapa: normal, media, naoClassificado, traco, descartada ou vazio."""
    if des.ajustadoOficial:   # valor do resultado publicado (ADR-007)
        if des.pontosFinais > 0:
            return formatarPontos(des.pontosFinais), "media" if des.destaqueMedia else "normal"
        return ("-", "traco") if des.inscrito else ("", "vazio")
    if des.atuouComoVoluntario:
        return (formatarPontos(des.pontosFinais) if des.pontosFinais > 0 else "-"), "media"
    if not des.inscrito:
        return "", "vazio"
    if des.descartada:
        return formatarPontos(des.pontosFinais), "descartada"
    if des.statusSigla == "NP" or (des.pontosFinais == 0 and des.colocacao is None):
        return "-", "traco"
    if des.colocacao is None and des.pontosFinais == 1:
        return formatarPontos(des.pontosFinais), "naoClassificado"
    return formatarPontos(des.pontosFinais), "normal"


def _paginar(categorias: list[tuple[str, list[ClassificacaoAtletaCategoria]]], capacidadePrimeira: int,
             capacidadeDemais: int) -> list[list[tuple[ClassificacaoAtletaCategoria, bool]]]:
    """Distribui as linhas em páginas mantendo cada categoria inteira na página sempre que ela couber."""
    paginas: list[list[tuple[ClassificacaoAtletaCategoria, bool]]] = [[]]

    def capacidade(indice: int) -> int:
        return capacidadePrimeira if indice == 0 else capacidadeDemais

    for _, fichas in categorias:
        atual = len(paginas) - 1
        if paginas[atual] and len(paginas[atual]) + len(fichas) > capacidade(atual) and len(fichas) <= capacidadeDemais:
            paginas.append([])
        for posicao, ficha in enumerate(fichas):
            if len(paginas[-1]) >= capacidade(len(paginas) - 1):
                paginas.append([])
            paginas[-1].append((ficha, posicao == len(fichas) - 1))
    return paginas


def _texto(page: Any, x0: float, x1: float, y: float, texto: str, fonte: Fonte, tamanho: float,
           alinhamento: str, cor: Cor) -> None:
    if texto:
        _inserirTextoAlinhado(page, x0, x1, y, texto, fonte, tamanho, alinhamento, cor)


def _desenharTrofeu(page: Any, cx: float, cy: float, cor: Cor) -> None:
    import pymupdf as fitz

    p = fitz.Point
    page.draw_polyline(
        [p(cx - 3.6, cy - 4.6), p(cx + 3.6, cy - 4.6), p(cx + 2.8, cy + 0.2), p(cx + 1.0, cy + 2.0),
         p(cx - 1.0, cy + 2.0), p(cx - 2.8, cy + 0.2), p(cx - 3.6, cy - 4.6)], color=cor, width=0.8,
    )
    for lado in (-1, 1):   # alças
        page.draw_bezier(p(cx + lado * 3.6, cy - 3.6), p(cx + lado * 6.4, cy - 3.8),
                         p(cx + lado * 6.0, cy - 0.4), p(cx + lado * 2.6, cy - 0.3), color=cor, width=0.8)
    page.draw_line(p(cx, cy + 2.0), p(cx, cy + 3.8), color=cor, width=0.8)
    page.draw_rect(fitz.Rect(cx - 2.4, cy + 3.8, cx + 2.4, cy + 4.9), color=cor, width=0.8)


def _desenharMedalha(page: Any, cx: float, cy: float, cor: Cor, digito: str, fonte: Fonte) -> None:
    import pymupdf as fitz

    p = fitz.Point
    for lado in (-1, 1):   # fitas
        page.draw_polyline(
            [p(cx + lado * 3.7, cy - 5.6), p(cx + lado * 1.3, cy - 5.6), p(cx - lado * 0.8, cy - 1.2),
             p(cx + lado * 1.6, cy - 1.2), p(cx + lado * 3.7, cy - 5.6)],
            color=cor, fill=cor, width=0.3, closePath=True,
        )
    page.draw_circle(p(cx, cy + 1.7), 3.7, color=cor, width=0.9)
    _inserirTextoAlinhado(page, cx - 4.0, cx + 4.0, cy + 3.7, digito, fonte, 5.8, "center", cor)


def _desenharPremio(page: Any, premio: str | None, topo: float, fontes: Fonte, fonteNegrito: Fonte,
                    rotuloArt42: str) -> None:
    """Célula de Premiação de uma linha (preenchimento, rótulo e ícone)."""
    import pymupdf as fitz

    if premio is None:
        return
    x0, x1 = X_PREMIO
    base = topo + 12.8
    if premio == PREMIO_ART42:
        page.draw_rect(fitz.Rect(x0, topo, x1, topo + ALT_LINHA), color=None, fill=LARANJA)
        _texto(page, x0, x1, base, rotuloArt42, fonteNegrito, 10.5, "center", PRETO)
        return
    numero = {PREMIO_TROFEU: "1", PREMIO_OURO: "1", PREMIO_PRATA: "2", PREMIO_BRONZE: "3"}[premio]
    if premio != PREMIO_TROFEU:
        page.draw_rect(fitz.Rect(x0, topo, x1, topo + ALT_LINHA), color=None, fill=CINZA_ESCURO)
    cor = {PREMIO_TROFEU: PRETO, PREMIO_OURO: OURO, PREMIO_PRATA: BRANCO, PREMIO_BRONZE: BRONZE}[premio]
    rotulo = f"{numero}°"
    largura = fonteNegrito[2].text_length(rotulo, fontsize=11.0) + 3.0 + 9.0
    xTexto = x0 + ((x1 - x0) - largura) / 2.0
    _texto(page, xTexto, xTexto + 40.0, base, rotulo, fonteNegrito, 11.0, "left", cor)
    xIcone = xTexto + fonteNegrito[2].text_length(rotulo, fontsize=11.0) + 3.0 + 4.5
    if premio == PREMIO_TROFEU:
        _desenharTrofeu(page, xIcone, topo + 9.0, cor)
    else:
        _desenharMedalha(page, xIcone, topo + 8.4, cor, numero, fonteNegrito)


def _colunasEtapas(numeros: list[int]) -> dict[int, float]:
    """Borda direita de cada coluna de etapa: a última fica fixa e as anteriores recuam um passo cada."""
    passo = PASSO_ETAPA if len(numeros) <= 4 else (X_ETAPA_DIR_ULTIMA - 539.5) / (len(numeros) - 1)
    return {et: X_ETAPA_DIR_ULTIMA - (len(numeros) - 1 - i) * passo for i, et in enumerate(numeros)}


def _desenharCabecalho(page: Any, topo: float, colunas: dict[int, float], fonteNegrito: Fonte,
                       fonteRegular: Fonte) -> None:
    import pymupdf as fitz

    page.draw_line(fitz.Point(X_ESQ, topo - 1.0), fitz.Point(X_DIR, topo - 1.0), color=PRETO, width=1.4)
    page.draw_rect(fitz.Rect(X_ESQ, topo, X_DIR, topo + ALT_CABECALHO), color=None, fill=AZUL)
    y = topo + 13.6
    _texto(page, X_CATEGORIA, X_CLASS_CENTRO, y, "Categoria", fonteRegular, 12.0, "left", BRANCO)
    _texto(page, X_CLASS_CENTRO - 20, X_CLASS_CENTRO + 20, y, "Class.", fonteNegrito, 9.4, "center", BRANCO)
    _texto(page, X_CBO_DIR - 30, X_CBO_DIR - 1.0, y, "CBO", fonteRegular, 12.0, "right", BRANCO)
    _texto(page, X_ATLETA, X_CLUBE, y, "Atleta", fonteRegular, 12.0, "left", BRANCO)
    _texto(page, X_CLUBE, X_CLUBE + 80, y, "Clube", fonteRegular, 12.0, "left", BRANCO)
    for et, direita in colunas.items():
        _texto(page, direita - 50, direita, y, f"{et}ª etapa", fonteRegular, 12.0, "right", BRANCO)
    _texto(page, X_TOTAL_DIR - 40, X_TOTAL_DIR, y, "Total", fonteRegular, 12.0, "right", BRANCO)
    _texto(page, X_PREMIO[0], X_PREMIO[1], y, "Premiação", fonteNegrito, 10.0, "center", BRANCO)


def _desenharLinha(page: Any, ficha: ClassificacaoAtletaCategoria, topo: float, zebra: bool, ultimaDaCategoria: bool,
                   colunas: dict[int, float], fontes: dict[str, Fonte], rotuloArt42: str) -> None:
    import pymupdf as fitz

    regular, negrito = fontes["regular"], fontes["bold"]
    if zebra:
        page.draw_rect(fitz.Rect(X_ESQ, topo, X_DIR, topo + ALT_LINHA), color=None, fill=CINZA)
    y = topo + 12.9
    _texto(page, X_CATEGORIA, X_CLASS_CENTRO, y, ficha.categoria, regular, 11.0, "left", PRETO)
    _texto(page, X_CLASS_CENTRO - 20, X_CLASS_CENTRO + 20, y, f"{ficha.colocacaoNaCategoria}º", regular, 10.0,
           "center", PRETO)
    _texto(page, X_CBO_DIR - 40, X_CBO_DIR, y, str(ficha.cbo), regular, 11.0, "right", PRETO)
    nome = ficha.nome
    while nome and regular[2].text_length(nome, fontsize=11.0) > X_CLUBE - X_ATLETA - 4.0:
        nome = nome[:-1]
    _texto(page, X_ATLETA, X_CLUBE, y, nome, regular, 11.0, "left", PRETO)
    _texto(page, X_CLUBE, X_CLUBE + 90, y, ficha.clubeSigla, regular, 11.0, "left", PRETO)

    for et, direita in colunas.items():
        texto, estilo = estiloDaCelula(ficha.etapas[et])
        if estilo == "vazio":
            continue
        caixa = fitz.Rect(direita - 33.0, topo, direita + 3.0, topo + ALT_LINHA)
        if estilo == "media":
            page.draw_rect(caixa, color=None, fill=AMARELO)
            _texto(page, direita - 40, direita, y, texto, negrito, 11.0, "right", PRETO)
        elif estilo == "naoClassificado":
            page.draw_rect(caixa, color=None, fill=LARANJA_CLARO)
            _texto(page, direita - 40, direita, y, texto, negrito, 11.0, "right", VERMELHO)
        elif estilo == "traco":
            _texto(page, direita - 40, direita - 14.0, y, texto, regular, 11.0, "right", CINZA_TRACO)
        elif estilo == "descartada":
            _texto(page, direita - 40, direita, y, texto, regular, 11.0, "right", CINZA_TRACO)
            largura = regular[2].text_length(texto, fontsize=11.0)
            page.draw_line(fitz.Point(direita - largura - 1.0, y - 3.4), fitz.Point(direita + 1.0, y - 3.4),
                           color=CINZA_TRACO, width=0.9)
        else:
            _texto(page, direita - 40, direita, y, texto, regular, 11.0, "right", PRETO)

    if ficha.pontuacaoTotal > 0:
        _texto(page, X_TOTAL_DIR - 40, X_TOTAL_DIR, y, formatarPontos(ficha.pontuacaoTotal), regular, 11.0, "right",
               PRETO)
    else:
        _texto(page, X_TOTAL_DIR - 40, X_TOTAL_DIR, y, "-", regular, 11.0, "right", CINZA_TRACO)
    _desenharPremio(page, classificarPremio(ficha), topo, regular, negrito, rotuloArt42)
    if ultimaDaCategoria:   # linha dupla ao fim de cada categoria
        for deslocamento in (ALT_LINHA - 0.4, ALT_LINHA + 1.2):
            page.draw_line(fitz.Point(X_ESQ, topo + deslocamento), fitz.Point(X_DIR, topo + deslocamento),
                           color=PRETO, width=0.7)


def _desenharQuadros(page: Any, topo: float, contagem: dict[str, int], regras: Any, fontes: dict[str, Fonte]) -> None:
    """Quadro de premiação (contagem por tipo) e legenda de cores, abaixo da linha de totais."""
    import pymupdf as fitz

    negrito = fontes["bold"]
    # Quadro de premiação
    xe, xd = X_ESQ, 159.0
    page.draw_rect(fitz.Rect(xe, topo, xd, topo + 21.0), color=None, fill=AZUL)
    _texto(page, xe, xd, topo + 14.5, "Premiação", negrito, 12.0, "center", BRANCO)
    alturaTabela = 21.0 + 4 * ALT_LINHA
    for i, premio in enumerate((PREMIO_TROFEU, PREMIO_OURO, PREMIO_PRATA, PREMIO_BRONZE)):
        y0 = topo + 21.0 + i * ALT_LINHA
        page.draw_rect(fitz.Rect(xe, y0, xd, y0 + ALT_LINHA), color=None, fill=AZUL_CLARO)
        numero = {PREMIO_TROFEU: "1", PREMIO_OURO: "1", PREMIO_PRATA: "2", PREMIO_BRONZE: "3"}[premio]
        _texto(page, xe + 12, xe + 44, y0 + 12.9, f"{numero}°", negrito, 11.0, "left", PRETO)
        if premio == PREMIO_TROFEU:
            _desenharTrofeu(page, xe + 54.0, y0 + 9.0, PRETO)
        else:
            _desenharMedalha(page, xe + 54.0, y0 + 8.4, PRETO, numero, negrito)
        _texto(page, xe + 90, xd - 8, y0 + 12.9, str(contagem.get(premio, 0)), negrito, 11.0, "right", PRETO)
    page.draw_rect(fitz.Rect(xe, topo, xd, topo + alturaTabela), color=PRETO, width=1.4)

    # Legenda
    xl0, xl1 = 170.0, 410.0
    page.draw_rect(fitz.Rect(xl0, topo, xl1, topo + 21.0), color=None, fill=AZUL)
    _texto(page, xl0, xl1, topo + 14.5, "Legenda", negrito, 12.0, "center", BRANCO)
    art = regras.artigos
    itens = (
        (CINZA_LEGENDA, PRETO, f"{rotuloArtigo(art.penalidadeChegada)} - Abandono da competição"),
        (VERMELHO, BRANCO, f"{rotuloArtigo(art.percursoAnulado)} - Percurso anulado"),
        (LARANJA_CLARO, VERMELHO, f"{rotuloArtigo(art.naoClassificado)} - Atleta não classificado"),
        (AMARELO, PRETO, f"{rotuloArtigo(art.voluntarios)} - Pontuação por média"),
        (LARANJA, PRETO, f"{rotuloArtigo(art.premiacao)} - Participação mínima"),
    )
    for i, (fundo, corTexto, texto) in enumerate(itens):
        y0 = topo + 21.0 + i * ALT_LINHA
        page.draw_rect(fitz.Rect(xl0, y0, xl1, y0 + ALT_LINHA), color=None, fill=fundo)
        _texto(page, xl0 + 3.0, xl1, y0 + 12.9, texto, negrito, 10.0, "left", corTexto)
    page.draw_rect(fitz.Rect(xl0, topo, xl1, topo + 21.0 + len(itens) * ALT_LINHA), color=PRETO, width=1.4)


def gerarPdfResultadoIndividualFinal(
    ano: int,
    edicaoRomanos: str,
    resultadoApuracao: dict[str, Any],
    caminhoSaidaPdf: str,
    caminhoLogo: str | None = None,
) -> None:
    """Gera o PDF do Resultado Individual final (layout da FECORI); a logo da edição entra se existir."""
    import pymupdf as fitz

    fichasPorCategoria: dict[str, list[ClassificacaoAtletaCategoria]] = resultadoApuracao["fichasPorCategoria"]
    regras = resultadoApuracao["regras"]
    categorias = [
        (c, fichasPorCategoria[c])
        for c in ordenarCategorias([c for c in fichasPorCategoria if not ehCategoriaSemPontuacao(c)])
    ]
    todas = [f for _, fichas in categorias for f in fichas]
    numeros = numerosEtapasRealizadas(resultadoApuracao)
    colunas = _colunasEtapas(numeros)
    fontes = _obterMapaFontesPdf()
    regular, negrito = fontes["regular"], fontes["bold"]
    rotuloArt42 = rotuloArtigo(regras.artigos.premiacao)

    capPrimeira = int((Y_LIMITE_LINHAS - (Y_CAB_PRIMEIRA + ALT_CABECALHO)) / ALT_LINHA)
    capDemais = int((Y_LIMITE_LINHAS - (Y_CAB_DEMAIS + ALT_CABECALHO)) / ALT_LINHA)
    paginas = _paginar(categorias, capPrimeira, capDemais)
    topoLinhas = [Y_CAB_PRIMEIRA + ALT_CABECALHO] + [Y_CAB_DEMAIS + ALT_CABECALHO] * (len(paginas) - 1)
    # A linha de totais e os quadros precisam caber depois da última linha; senão vão para uma página própria.
    alturaFinal = ALT_LINHA + 28.0 + 21.0 + 5 * ALT_LINHA
    paginaSoQuadros = topoLinhas[-1] + len(paginas[-1]) * ALT_LINHA + alturaFinal > ALTURA - 20.0
    if paginaSoQuadros:
        paginas.append([])
        topoLinhas.append(Y_CAB_DEMAIS)

    contagemPremios: dict[str, int] = {}
    for f in todas:
        premio = classificarPremio(f)
        if premio:
            contagemPremios[premio] = contagemPremios.get(premio, 0) + 1
    contagemEtapas = _contarInscricoesPorEtapa(todas, numeros)
    logoBytes = carregarBytesLogoSemFundo(caminhoLogo)
    carimbo = datetime.now().strftime("%d/%m/%Y - %H:%M")

    doc = fitz.open()
    indiceGlobal = 0
    for numeroPagina, linhasPagina in enumerate(paginas, start=1):
        page = doc.new_page(width=LARGURA, height=ALTURA)
        if numeroPagina == 1:
            if logoBytes:
                page.insert_image(fitz.Rect(14.0, 27.0, 91.0, 104.0), stream=logoBytes, keep_proportion=True)
            _texto(page, 100.0, 740.0, 61.0, "Resultado Individual do", negrito, 25.0, "center", PRETO)
            _texto(page, 100.0, 740.0, 93.0, f"{edicaoRomanos} Campeonato Cearense de Orientação", negrito, 25.0,
                   "center", PRETO)
            _texto(page, 700.0, 826.0, 76.0, "FECORI", negrito, 21.0, "right", (0.15, 0.15, 0.15))
        if linhasPagina or not paginaSoQuadros or numeroPagina != len(paginas):
            _desenharCabecalho(page, Y_CAB_PRIMEIRA if numeroPagina == 1 else Y_CAB_DEMAIS, colunas, negrito, regular)
        y = topoLinhas[numeroPagina - 1]
        for ficha, ultima in linhasPagina:
            _desenharLinha(page, ficha, y, indiceGlobal % 2 == 0, ultima, colunas, fontes, rotuloArt42)
            indiceGlobal += 1
            y += ALT_LINHA
        if numeroPagina == len(paginas):
            page.draw_line(fitz.Point(X_ESQ, y), fitz.Point(X_DIR, y), color=PRETO, width=0.8)
            _texto(page, X_CATEGORIA, X_CLASS_CENTRO + 40, y + 13.0, "Total", negrito, 12.0, "left", PRETO)
            _texto(page, X_ATLETA, X_CLUBE, y + 13.0, str(len(todas)), negrito, 12.0, "center", PRETO)
            for et, direita in colunas.items():
                _texto(page, direita - 40, direita, y + 13.0, str(contagemEtapas[et]), negrito, 12.0, "right", PRETO)
            for deslocamento in (ALT_LINHA, ALT_LINHA + 1.6):
                page.draw_line(fitz.Point(X_ESQ, y + deslocamento), fitz.Point(X_DIR, y + deslocamento),
                               color=PRETO, width=0.7)
            _desenharQuadros(page, y + ALT_LINHA + 28.0, contagemPremios, regras, fontes)
        _texto(page, X_ESQ, 200.0, Y_RODAPE, carimbo, regular, 9.0, "left", PRETO)
        _texto(page, 700.0, X_DIR, Y_RODAPE, f"{numeroPagina} / {len(paginas)}", regular, 9.0, "right", PRETO)

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaidaPdf)), exist_ok=True)
    doc.save(caminhoSaidaPdf)
    doc.close()
