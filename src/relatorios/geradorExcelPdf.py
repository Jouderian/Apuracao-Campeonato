# -*- coding: utf-8 -*-
"""Geração de planilha Excel (.xlsx) e relatórios PDF (Individual/Parcial e Clubes) da apuração."""
from datetime import datetime
from decimal import Decimal
import io
import os
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.motorCalculo.pontuacao import (
    ClassificacaoAtletaCategoria,
    DesempenhoEtapaCalculado,
    ehCategoriaSemPontuacao,
)
from src.relatorios.geradorMarkdown import formatarMoedaPontos

ETAPAS_CAMPEONATO: tuple[int, ...] = (1, 2, 3, 4)


def sanitizarCelulaExcel(texto: str) -> str:
    """Previne injeção de fórmula em planilhas Excel/CSV (code-standards.md, item 5)."""
    limpo = str(texto).strip()
    if limpo.startswith(('=', '+', '-', '@')):
        return f"'{limpo}"
    return limpo


def formatarPontoTabelaParcial(valor: Decimal) -> str:
    """Formata pontuação para a tabela parcial (inteiro se exato, ou decimal enxuto com vírgula)."""
    q = valor.quantize(Decimal("0.01"))
    if q == q.to_integral_value():
        return str(int(q))
    texto = f"{q:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def carregarBytesLogoSemFundo(caminhoLogo: str | None) -> bytes | None:
    """Carrega a logo do campeonato e torna transparente o fundo claro (#F7F7F7/#FFFFFF)."""
    if not caminhoLogo or not os.path.isfile(caminhoLogo):
        return None
    from PIL import Image, ImageChops

    with Image.open(caminhoLogo) as img:
        rgba = img.convert("RGBA")
        r, g, b, a = rgba.split()
        claro = lambda v: 255 if v >= 240 else 0  # noqa: E731
        fundo = ImageChops.multiply(ImageChops.multiply(r.point(claro), g.point(claro)), b.point(claro))
        rgba.putalpha(ImageChops.subtract(a, fundo))
        bbox = rgba.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue()


def _obterMapaFontesPdf() -> dict[str, tuple[str, str | None, Any]]:
    """Retorna tuplas (fontname, fontfile, fitz.Font) usando Calibri/Consolas no Windows ou Helvetica no Linux."""
    import pymupdf as fitz

    candidatos = {
        "regular": ("calibri", r"C:\Windows\Fonts\calibri.ttf", "helv"),
        "bold": ("calibrib", r"C:\Windows\Fonts\calibrib.ttf", "hebo"),
        "italic": ("calibrii", r"C:\Windows\Fonts\calibrii.ttf", "heit"),
        "mono": ("consola", r"C:\Windows\Fonts\consola.ttf", "cour"),
    }
    mapa: dict[str, tuple[str, str | None, Any]] = {}
    for chave, ( apelido, caminhoTtf, fallback ) in candidatos.items():
        if os.path.isfile(caminhoTtf):
            fonteObj = fitz.Font(fontfile=caminhoTtf)
            mapa[chave] = (apelido, caminhoTtf, fonteObj)
        else:
            fonteObj = fitz.Font(fontname=fallback)
            mapa[chave] = (fallback, None, fonteObj)
    return mapa


def _inserirTextoAlinhado(
    page: Any,
    x0: float,
    x1: float,
    yBase: float,
    texto: str,
    estiloFonte: tuple[str, str | None, Any],
    fontsize: float,
    alinhamento: str,
    cor: tuple[float, float, float],
) -> float:
    """Insere texto em uma linha de base (yBase) com alinhamento exato ('left', 'center', 'right').

    Retorna a coordenada X imediatamente após o término do texto inserido.
    """
    import pymupdf as fitz

    fontname, fontfile, fonteObj = estiloFonte
    larguraTxt = fonteObj.text_length(texto, fontsize=fontsize)
    if alinhamento == "center":
        x = x0 + ((x1 - x0) - larguraTxt) / 2.0
    elif alinhamento == "right":
        x = x1 - larguraTxt
    else:
        x = x0

    page.insert_text(
        fitz.Point(x, yBase),
        texto,
        fontsize=fontsize,
        fontname=fontname,
        fontfile=fontfile,
        color=cor,
    )
    return x + larguraTxt


def _descreverEtapaPlanilha(des: DesempenhoEtapaCalculado) -> str:
    if not des.inscrito and not des.atuouComoVoluntario:
        return "-"
    if des.atuouComoVoluntario:
        return "VOL"
    if des.colocacao is not None:
        return f"{des.colocacao}º"
    return des.statusSigla


def _coletarLinhasTabelaParcial(
    resultadoApuracao: dict[str, Any],
) -> list[ClassificacaoAtletaCategoria]:
    fichasPorCat: dict[str, list[ClassificacaoAtletaCategoria]] = resultadoApuracao["fichasPorCategoria"]
    linhas: list[ClassificacaoAtletaCategoria] = []
    for categoria in sorted(fichasPorCat.keys()):
        if ehCategoriaSemPontuacao(categoria):
            continue
        for f in fichasPorCat[categoria]:
            linhas.append(f)
    return linhas


def gerarPlanilhaExcelApuracao(
    ano: int,
    edicao: str,
    edicaoRomanos: str,
    resultadoApuracao: dict[str, Any],
    caminhoSaidaXlsx: str,
) -> None:
    """Gera o arquivo Excel (.xlsx) com abas resultadoParcial, resultadoClubes, resultadoIndividual e memoriaClubesTop3."""
    wb = Workbook()

    fonteTitulo = Font(name="Calibri", size=14, bold=True, color="000000")
    fonteCabecalho = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fonteTotalBranca = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    fonteNegrito = Font(name="Calibri", size=10, bold=True)
    fonteNormal = Font(name="Calibri", size=10)
    fonteRosa = Font(name="Calibri", size=10, color="9C0006")
    fonteDescarte = Font(name="Calibri", size=10, strike=True, color="808080")

    preenchimentoCabecalho = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    preenchimentoCinzaParcial = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    preenchimentoRosaDuplicado = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    preenchimentoZebraClubes = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    bordaFina = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )

    # 1. Aba: resultadoParcial (idêntica ao layout do PDF de Resultado Parcial dos Atletas)
    wsParcial = wb.active
    wsParcial.title = "resultadoParcial"
    wsParcial["A1"] = f"Resultado parcial do {edicaoRomanos} Campeonato Cearense de Orientação NÃO OFICIAL"
    wsParcial["A1"].font = fonteTitulo
    wsParcial.append([])

    cabecalhosParcial = ["Categoria", "Class", "CBO", "Atleta", "Clube", "1", "2", "3", "4", "Total"]
    wsParcial.append(cabecalhosParcial)
    for colIdx in range(1, len(cabecalhosParcial) + 1):
        cel = wsParcial.cell(row=3, column=colIdx)
        cel.font = fonteCabecalho
        cel.fill = preenchimentoCabecalho
        cel.alignment = Alignment(
            horizontal="left" if colIdx in (1, 4, 5) else ("right" if colIdx == 3 else "center"),
            vertical="center",
        )

    linhasParcial = _coletarLinhasTabelaParcial(resultadoApuracao)
    contagemEtapas = {et: 0 for et in ETAPAS_CAMPEONATO}
    for idx, f in enumerate(linhasParcial, start=1):
        rowNum = 3 + idx
        notasCols: list[float | int | str] = []
        for et in ETAPAS_CAMPEONATO:
            des = f.etapas[et]
            if not des.inscrito and not des.atuouComoVoluntario:
                notasCols.append("")
            else:
                contagemEtapas[et] += 1
                q = des.pontosFinais.quantize(Decimal("0.01"))
                notasCols.append(int(q) if q == q.to_integral_value() else float(q))

        totQ = f.pontuacaoTotal.quantize(Decimal("0.01"))
        totVal: int | float = int(totQ) if totQ == totQ.to_integral_value() else float(totQ)
        wsParcial.append([
            sanitizarCelulaExcel(f.categoria),
            f.colocacaoNaCategoria,
            int(f.cbo),
            sanitizarCelulaExcel(f.nome),
            sanitizarCelulaExcel(f.clubeSigla),
            notasCols[0],
            notasCols[1],
            notasCols[2],
            notasCols[3],
            totVal,
        ])
        for colIdx in range(1, 11):
            cel = wsParcial.cell(row=rowNum, column=colIdx)
            cel.font = fonteNormal
            if colIdx < 10 and idx % 2 == 1:
                cel.fill = preenchimentoCinzaParcial
            if colIdx == 4 and f.competiuEmMultiplasCategorias:
                cel.fill = preenchimentoRosaDuplicado
                cel.font = fonteRosa
            if colIdx == 10:
                cel.fill = preenchimentoCabecalho
                cel.font = fonteTotalBranca
            if colIdx in (2, 6, 7, 8, 9, 10):
                cel.alignment = Alignment(horizontal="center")
            elif colIdx == 3:
                cel.alignment = Alignment(horizontal="right")

    linhaTotParcial = 4 + len(linhasParcial)
    wsParcial.append([
        "Total", "", "", len(linhasParcial), "",
        contagemEtapas[1], contagemEtapas[2], contagemEtapas[3], contagemEtapas[4], "",
    ])
    for colIdx in range(1, 11):
        cel = wsParcial.cell(row=linhaTotParcial, column=colIdx)
        cel.font = fonteNegrito
        if colIdx in (4, 6, 7, 8, 9):
            cel.alignment = Alignment(horizontal="center")

    # 2. Aba: resultadoClubes
    wsClubes = wb.create_sheet(title="resultadoClubes")
    wsClubes["A1"] = f"Resultado de Clubes — {edicao} ({ano})"
    wsClubes["A1"].font = fonteTitulo

    cabecalhosClubes = [
        "Class.", "Clube", "Nome Completo", "Federação", "Atletas",
        "1ª Etapa", "2ª Etapa", "3ª Etapa", "4ª Etapa", "Total Pontos",
    ]
    wsClubes.append([])
    wsClubes.append(cabecalhosClubes)
    for colIdx in range(1, len(cabecalhosClubes) + 1):
        cel = wsClubes.cell(row=3, column=colIdx)
        cel.font = fonteCabecalho
        cel.fill = preenchimentoCabecalho
        cel.alignment = Alignment(horizontal="center", vertical="center")

    for idx, c in enumerate(resultadoApuracao["classificacaoClubes"], start=1):
        linhaIdx = 3 + idx
        valores = [
            f"{idx}º",
            sanitizarCelulaExcel(c["sigla"]),
            sanitizarCelulaExcel(c["nome"]),
            sanitizarCelulaExcel(c.get("federacaoSigla") or "-"),
            int(c["qtdAtletas"]),
            float(c["pontosPorEtapa"].get(1, Decimal("0.00"))),
            float(c["pontosPorEtapa"].get(2, Decimal("0.00"))),
            float(c["pontosPorEtapa"].get(3, Decimal("0.00"))),
            float(c["pontosPorEtapa"].get(4, Decimal("0.00"))),
            float(c["totalPontos"]),
        ]
        wsClubes.append(valores)
        for colIdx in range(1, len(valores) + 1):
            cel = wsClubes.cell(row=linhaIdx, column=colIdx)
            cel.font = fonteNegrito if idx <= 3 else fonteNormal
            cel.border = bordaFina
            if idx % 2 == 1:
                cel.fill = preenchimentoZebraClubes
            if colIdx in (1, 4, 5):
                cel.alignment = Alignment(horizontal="center")
            elif colIdx >= 6:
                cel.number_format = "#,##0.00"
                cel.alignment = Alignment(horizontal="right")

    # 3. Aba: resultadoIndividual
    wsIndiv = wb.create_sheet(title="resultadoIndividual")
    wsIndiv["A1"] = f"Classificação Individual Detalhada — {edicao} ({ano})"
    wsIndiv["A1"].font = fonteTitulo
    wsIndiv.append([])

    cabecalhosIndiv = [
        "Categoria", "Col.", "CBO", "Atleta", "Clube",
        "E1 Pts", "E1 Sit.", "E2 Pts", "E2 Sit.", "E3 Pts", "E3 Sit.", "E4 Pts", "E4 Sit.",
        "Etapa Descartada", "Total Pontos", "Elegível Premiação (Art. 39)",
    ]
    wsIndiv.append(cabecalhosIndiv)
    for colIdx in range(1, len(cabecalhosIndiv) + 1):
        cel = wsIndiv.cell(row=3, column=colIdx)
        cel.font = fonteCabecalho
        cel.fill = preenchimentoCabecalho
        cel.alignment = Alignment(horizontal="center", vertical="center")

    linhaAtual = 4
    for f in linhasParcial:
        colStr = f"{f.colocacaoFinal}º" if f.colocacaoFinal > 0 else ("Art. 32" if not f.categoriaValidaFinal else "-")
        e1, e2, e3, e4 = f.etapas[1], f.etapas[2], f.etapas[3], f.etapas[4]
        valores = [
            sanitizarCelulaExcel(f.categoria),
            colStr,
            int(f.cbo),
            sanitizarCelulaExcel(f.nome),
            sanitizarCelulaExcel(f.clubeSigla),
            float(e1.pontosFinais), _descreverEtapaPlanilha(e1),
            float(e2.pontosFinais), _descreverEtapaPlanilha(e2),
            float(e3.pontosFinais), _descreverEtapaPlanilha(e3),
            float(e4.pontosFinais), _descreverEtapaPlanilha(e4),
            f"{f.etapaDescartada}ª" if f.etapaDescartada else "-",
            float(f.pontuacaoTotal),
            "Sim" if f.elegivelPremiacao else f"Não ({f.etapasParticipadas}/4)",
        ]
        wsIndiv.append(valores)
        ehPodio = 1 <= f.colocacaoFinal <= 3
        for colIdx in range(1, len(valores) + 1):
            cel = wsIndiv.cell(row=linhaAtual, column=colIdx)
            cel.font = fonteNegrito if ehPodio else fonteNormal
            cel.border = bordaFina
            if colIdx == 4 and f.competiuEmMultiplasCategorias:
                cel.fill = preenchimentoRosaDuplicado
                cel.font = fonteRosa
            if colIdx in (6, 8, 10, 12, 15):
                cel.number_format = "#,##0.00"
                cel.alignment = Alignment(horizontal="right")
            elif colIdx in (1, 2, 3, 5, 7, 9, 11, 13, 14, 16):
                cel.alignment = Alignment(horizontal="center")

        if f.etapaDescartada in ETAPAS_CAMPEONATO:
            colPtsDesc = 6 + (f.etapaDescartada - 1) * 2
            wsIndiv.cell(row=linhaAtual, column=colPtsDesc).font = fonteDescarte
            wsIndiv.cell(row=linhaAtual, column=colPtsDesc + 1).font = fonteDescarte

        linhaAtual += 1

    # 4. Aba: memoriaClubesTop3
    wsMem = wb.create_sheet(title="memoriaClubesTop3")
    wsMem["A1"] = f"Memória de Cálculo dos Clubes (Top 3 por Categoria e Etapa) — {edicao} ({ano})"
    wsMem["A1"].font = fonteTitulo
    wsMem.append([])
    cabecalhosMem = ["Etapa", "Clube", "Categoria", "Ordem no Clube", "CBO", "Atleta", "Pontos Somados"]
    wsMem.append(cabecalhosMem)
    for colIdx in range(1, len(cabecalhosMem) + 1):
        cel = wsMem.cell(row=3, column=colIdx)
        cel.font = fonteCabecalho
        cel.fill = preenchimentoCabecalho
        cel.alignment = Alignment(horizontal="center")

    linhaMem = 4
    for c in resultadoApuracao["classificacaoClubes"]:
        for et in sorted(c["detalheTop3PorEtapa"].keys()):
            for cat, topList in sorted(c["detalheTop3PorEtapa"][et].items()):
                for ordem, item in enumerate(topList, start=1):
                    wsMem.append([
                        f"{et}ª",
                        sanitizarCelulaExcel(c["sigla"]),
                        sanitizarCelulaExcel(cat),
                        f"{ordem}º",
                        int(item["cbo"]),
                        sanitizarCelulaExcel(item["nome"]),
                        float(Decimal(item["pontos"])),
                    ])
                    wsMem.cell(row=linhaMem, column=7).number_format = "#,##0.00"
                    linhaMem += 1

    for ws in (wsParcial, wsClubes, wsIndiv, wsMem):
        for col in ws.columns:
            maxLen = max((len(str(cell.value or "")) for cell in col), default=10)
            colLetter = get_column_letter(col[0].column)
            ws.column_dimensions[colLetter].width = min(max(maxLen + 3, 8), 42)

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaidaXlsx)), exist_ok=True)
    wb.save(caminhoSaidaXlsx)


# --- Geometria e cores do PDF de Resultado Parcial (A4 retrato, 595.32 x 841.92 pt) ---------------------
LARGURA_PAGINA = 595.32
ALTURA_PAGINA = 841.92
X_ESQ, X_DIR = 15.60, 579.48
X_TOTAL_ESQ = 543.72
TOPO_CABECALHO = 45.00
ALTURA_CABECALHO = 15.96
ALTURA_LINHA = 16.32
LINHAS_POR_PAGINA = 45
LIMITE_LINHAS_ULTIMA_PAGINA = 36   # acima disso, o bloco de totais e observação vai para uma página nova
Y_BASELINE_TITULO = 28.5
Y_RODAPE = 823.5

# Colunas da tabela (x0, x1)
COL_CATEGORIA = (17.0, 76.0)
COL_CLASS = (76.0, 106.0)
COL_CBO = (106.0, 141.3)
COL_ATLETA = (145.0, 360.0)
COL_ATLETA_FUNDO = (143.16, 362.16)
COL_CLUBE = (363.8, 434.0)
COLS_ETAPAS: dict[int, tuple[float, float]] = {
    1: (434.0, 461.4),
    2: (461.4, 488.8),
    3: (488.8, 516.2),
    4: (516.2, 543.72),
}

COR_AZUL = (0.267, 0.447, 0.769)        # #4472C4
COR_CINZA = (0.851, 0.851, 0.851)       # #D9D9D9
COR_ROSA_FUNDO = (1.0, 0.780, 0.808)    # #FFC7CE
COR_ROSA_TEXTO = (0.612, 0.0, 0.024)    # #9C0006
COR_VERMELHO = (1.0, 0.0, 0.0)          # #FF0000
COR_PRETO = (0.0, 0.0, 0.0)
COR_BRANCO = (1.0, 1.0, 1.0)


def _contarInscricoesPorEtapa(linhas: list[ClassificacaoAtletaCategoria]) -> dict[int, int]:
    contagem = {et: 0 for et in ETAPAS_CAMPEONATO}
    for f in linhas:
        for et in ETAPAS_CAMPEONATO:
            des = f.etapas[et]
            if des.inscrito or des.atuouComoVoluntario:
                contagem[et] += 1
    return contagem


def _paginarLinhasParcial(linhas: list[ClassificacaoAtletaCategoria]) -> list[list[ClassificacaoAtletaCategoria]]:
    paginas = [linhas[i:i + LINHAS_POR_PAGINA] for i in range(0, len(linhas), LINHAS_POR_PAGINA)] or [[]]
    if len(paginas[-1]) > LIMITE_LINHAS_ULTIMA_PAGINA:
        paginas.append([])
    return paginas


def _montarTextoObservacao(
    resultadoApuracao: dict[str, Any],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Monta as duas primeiras linhas do bloco OBSERVAÇÃO como trechos (texto, estilo).

    Estilos: 'r' regular, 'b' negrito, 'i' itálico.
    """
    etapasComVol = set(resultadoApuracao.get("etapasComVoluntarios", []))
    etapasComArb = set(resultadoApuracao.get("etapasComArbitros", []))
    pendentesVol = [et for et in ETAPAS_CAMPEONATO if et not in etapasComVol]
    pendentesArb = [et for et in ETAPAS_CAMPEONATO if et not in etapasComArb]

    if not etapasComVol and not etapasComArb:
        return (
            [("OBSERVAÇÃO:", "b"), (" Este resultado não é oficial e não inclui os ", "r"), ("voluntários", "i")],
            [
                ("que participaram das etapas nem os ", "r"), ("árbitros", "i"),
                (" convocados pela ", "r"), ("FECORI", "b"), (".", "r"),
            ],
        )
    if pendentesVol:
        etStr = ", ".join(f"{e}ª" for e in pendentesVol)
        inicioL1 = [("OBSERVAÇÃO:", "b"), (" Este resultado não é oficial e ainda não inclui os ", "r"), ("voluntários", "i")]
        if not pendentesArb:
            trecho = f"da {etStr} etapa (os " if len(pendentesVol) == 1 else f"das etapas ({etStr}) (os "
            return (
                inicioL1,
                [
                    (trecho, "r"), ("árbitros", "i"), (" convocados pela ", "r"),
                    ("FECORI", "b"), (" já estão incluídos).", "r"),
                ],
            )
        trecho = f"da {etStr} etapa nem eventuais " if len(pendentesVol) == 1 else f"das etapas ({etStr}) nem eventuais "
        return (
            inicioL1,
            [(trecho, "r"), ("árbitros", "i"), (" pendentes na ", "r"), ("FECORI", "b"), (".", "r")],
        )
    return (
        [("OBSERVAÇÃO:", "b"), (" Este resultado não é oficial e contempla os ", "r"), ("voluntários", "i")],
        [
            ("informados pelas etapas e os ", "r"), ("árbitros", "i"),
            (" convocados pela ", "r"), ("FECORI", "b"), (".", "r"),
        ],
    )


def _desenharTituloParcial(
    page: Any, edicaoRomanos: str, logoBytes: bytes | None, fBold: tuple[str, str | None, Any]
) -> None:
    """Título com logo opcional à esquerda e o texto 'NÃO OFICIAL' alinhado à direita da folha."""
    import pymupdf as fitz

    if logoBytes:
        page.insert_image(fitz.Rect(X_ESQ, 5.0, X_ESQ + 35.0, 42.5), stream=logoBytes, keep_proportion=True)
        xTitulo, tamFonte = X_ESQ + 40.0, 12.8
    else:
        xTitulo, tamFonte = X_ESQ, 13.2

    texto = f"Resultado parcial do {edicaoRomanos} Campeonato Cearense de Orientação"
    _inserirTextoAlinhado(page, xTitulo, X_DIR, Y_BASELINE_TITULO, texto, fBold, tamFonte, "left", COR_PRETO)
    _inserirTextoAlinhado(page, xTitulo, X_DIR, Y_BASELINE_TITULO, "NÃO OFICIAL", fBold, tamFonte, "right", COR_VERMELHO)


def _desenharCabecalhoTabelaParcial(page: Any, fBold: tuple[str, str | None, Any]) -> None:
    import pymupdf as fitz

    page.draw_rect(
        fitz.Rect(X_ESQ, TOPO_CABECALHO, X_DIR, TOPO_CABECALHO + ALTURA_CABECALHO), color=None, fill=COR_AZUL
    )
    for y in (TOPO_CABECALHO, TOPO_CABECALHO + ALTURA_CABECALHO):
        page.draw_line(fitz.Point(X_ESQ, y), fitz.Point(X_DIR, y), color=COR_PRETO, width=1.0)

    y = TOPO_CABECALHO + 11.6
    _inserirTextoAlinhado(page, *COL_CATEGORIA, y, "Categoria", fBold, 11.2, "left", COR_BRANCO)
    _inserirTextoAlinhado(page, *COL_CLASS, y, "Class", fBold, 9.4, "center", COR_BRANCO)
    _inserirTextoAlinhado(page, *COL_CBO, y, "CBO", fBold, 11.2, "right", COR_BRANCO)
    _inserirTextoAlinhado(page, *COL_ATLETA, y, "Atleta", fBold, 11.2, "left", COR_BRANCO)
    _inserirTextoAlinhado(page, *COL_CLUBE, y, "Clube", fBold, 11.2, "left", COR_BRANCO)
    for et, (x0, x1) in COLS_ETAPAS.items():
        _inserirTextoAlinhado(page, x0, x1, y, str(et), fBold, 9.4, "center", COR_BRANCO)
    _inserirTextoAlinhado(page, X_TOTAL_ESQ, X_DIR, y, "Total", fBold, 11.2, "center", COR_BRANCO)


def _desenharLinhaAtletaParcial(
    page: Any,
    f: ClassificacaoAtletaCategoria,
    yLinha: float,
    ehLinhaCinza: bool,
    fontes: dict[str, tuple[str, str | None, Any]],
) -> None:
    import pymupdf as fitz

    fRegular, fBold = fontes["regular"], fontes["bold"]
    page.draw_rect(
        fitz.Rect(X_ESQ, yLinha, X_TOTAL_ESQ, yLinha + ALTURA_LINHA),
        color=None,
        fill=COR_CINZA if ehLinhaCinza else COR_BRANCO,
    )
    if f.competiuEmMultiplasCategorias:
        page.draw_rect(
            fitz.Rect(COL_ATLETA_FUNDO[0], yLinha, COL_ATLETA_FUNDO[1], yLinha + ALTURA_LINHA),
            color=None,
            fill=COR_ROSA_FUNDO,
        )
    page.draw_rect(fitz.Rect(X_TOTAL_ESQ, yLinha, X_DIR, yLinha + ALTURA_LINHA), color=None, fill=COR_AZUL)

    y = yLinha + 11.6
    corNome = COR_ROSA_TEXTO if f.competiuEmMultiplasCategorias else COR_PRETO
    _inserirTextoAlinhado(page, 16.9, COL_CATEGORIA[1], y, f.categoria, fRegular, 10.2, "left", COR_PRETO)
    _inserirTextoAlinhado(page, *COL_CLASS, y, str(f.colocacaoNaCategoria), fRegular, 10.2, "center", COR_PRETO)
    _inserirTextoAlinhado(page, 104.0, COL_CBO[1], y, str(f.cbo), fRegular, 10.2, "right", COR_PRETO)
    _inserirTextoAlinhado(page, COL_ATLETA[0], 361.0, y, f.nome[:42], fRegular, 10.2, "left", corNome)
    _inserirTextoAlinhado(page, *COL_CLUBE, y, f.clubeSigla[:15], fRegular, 10.2, "left", COR_PRETO)

    for et, (x0, x1) in COLS_ETAPAS.items():
        des = f.etapas[et]
        if des.inscrito or des.atuouComoVoluntario:
            texto = formatarPontoTabelaParcial(des.pontosFinais)
            _inserirTextoAlinhado(page, x0, x1, y, texto, fRegular, 10.0, "center", COR_PRETO)

    texto = formatarPontoTabelaParcial(f.pontuacaoTotal)
    _inserirTextoAlinhado(page, X_TOTAL_ESQ, X_DIR, y, texto, fBold, 10.2, "center", COR_BRANCO)


def _desenharTotaisEObservacao(
    page: Any,
    yLinha: float,
    totalAtletas: int,
    contagemEtapas: dict[int, int],
    resultadoApuracao: dict[str, Any],
    fontes: dict[str, tuple[str, str | None, Any]],
) -> None:
    """Linha de totais de inscrições por etapa e bloco OBSERVAÇÃO em vermelho (última página)."""
    import pymupdf as fitz

    fBold = fontes["bold"]
    estilos = {"r": fontes["regular"], "b": fBold, "i": fontes["italic"], "m": fontes["mono"]}

    page.draw_line(fitz.Point(X_ESQ, yLinha), fitz.Point(X_DIR, yLinha), color=COR_PRETO, width=0.8)
    yBaseTot = yLinha + 11.8
    _inserirTextoAlinhado(page, *COL_CATEGORIA, yBaseTot, "Total", fBold, 11.2, "left", COR_PRETO)
    _inserirTextoAlinhado(page, *COL_ATLETA_FUNDO, yBaseTot, str(totalAtletas), fBold, 11.2, "center", COR_PRETO)
    for et, (x0, x1) in COLS_ETAPAS.items():
        _inserirTextoAlinhado(page, x0, x1, yBaseTot, str(contagemEtapas[et]), fBold, 11.2, "center", COR_PRETO)
    yFimTot = yLinha + ALTURA_LINHA
    page.draw_line(fitz.Point(X_ESQ, yFimTot), fitz.Point(X_DIR, yFimTot), color=COR_PRETO, width=0.8)
    page.draw_line(fitz.Point(X_ESQ, yFimTot + 2.0), fitz.Point(X_DIR, yFimTot + 2.0), color=COR_PRETO, width=0.8)

    linhasL1, linhasL2 = _montarTextoObservacao(resultadoApuracao)
    yObs = yFimTot + 44.0
    yObs2 = yObs + 19.0
    yObs3 = yObs2 + 38.0
    yObs4 = yObs3 + 19.0
    yObs5 = yObs4 + 19.0
    blocos = [
        (yObs, linhasL1),
        (yObs2, linhasL2),
        (yObs3, [
            ("Caso identifique alguma inconformidade, envie um ", "r"),
            ("eMail", "i"),
            (" para", "r"),
        ]),
        (yObs4, [
            ("jouderian@gmail.com", "m"),
            (", para que possamos analisá-la e implementar", "r"),
        ]),
        (yObs5, [("melhorias nas próximas edições.", "r")]),
    ]
    for yBase, trechos in blocos:
        xCur = 18.0
        for txt, est in trechos:
            xCur = _inserirTextoAlinhado(page, xCur, X_DIR, yBase, txt, estilos[est], 14.5, "left", COR_VERMELHO)


def gerarPdfResultadoParcialAtletas(
    ano: int,
    edicaoRomanos: str,
    resultadoApuracao: dict[str, Any],
    caminhosSaidaPdf: list[str],
    caminhoLogo: str | None = None,
) -> None:
    """Gera o PDF de Resultado Parcial dos Atletas seguindo o modelo da FECORI.

    Sem `caminhoLogo` o título começa na margem esquerda (caso do resultado parcial, que é não oficial).
    """
    import pymupdf as fitz

    linhas = _coletarLinhasTabelaParcial(resultadoApuracao)
    logoBytes = carregarBytesLogoSemFundo(caminhoLogo)
    carimbo = datetime.now().strftime("%d/%m/%Y - %H:%M")
    fontes = _obterMapaFontesPdf()
    fRegular, fBold = fontes["regular"], fontes["bold"]

    paginasLinhas = _paginarLinhasParcial(linhas)
    totalPaginas = len(paginasLinhas)
    contagemEtapas = _contarInscricoesPorEtapa(linhas)
    doc = fitz.open()

    for idxPag, fatia in enumerate(paginasLinhas, start=1):
        page = doc.new_page(width=LARGURA_PAGINA, height=ALTURA_PAGINA)
        _desenharTituloParcial(page, edicaoRomanos, logoBytes, fBold)
        _desenharCabecalhoTabelaParcial(page, fBold)

        yLinha = TOPO_CABECALHO + ALTURA_CABECALHO
        for idxLinhaPag, f in enumerate(fatia, start=1):
            _desenharLinhaAtletaParcial(page, f, yLinha, idxLinhaPag % 2 == 1, fontes)
            yLinha += ALTURA_LINHA

        if idxPag == totalPaginas:
            _desenharTotaisEObservacao(page, yLinha, len(linhas), contagemEtapas, resultadoApuracao, fontes)

        _inserirTextoAlinhado(page, 15.24, 200.0, Y_RODAPE, carimbo, fRegular, 10.2, "left", COR_PRETO)
        _inserirTextoAlinhado(
            page, 480.0, 580.25, Y_RODAPE, f"{idxPag} / {totalPaginas}", fRegular, 10.2, "right", COR_PRETO
        )

    for caminho in caminhosSaidaPdf:
        os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
        doc.save(caminho)
    doc.close()


def gerarPdfResultadoClubes(
    ano: int,
    edicaoRomanos: str,
    resultadoApuracao: dict[str, Any],
    caminhoSaidaPdf: str,
    nomeArquivoPlanilha: str,
    caminhoLogo: str | None = None,
) -> None:
    """Gera o PDF oficial de Resultado de Clubes no layout paisagem da FECORI com a logo da edição."""
    import pymupdf as fitz

    doc = fitz.open()
    largura, altura = 841.92, 595.32
    page = doc.new_page(width=largura, height=altura)
    fontes = _obterMapaFontesPdf()
    fRegular = fontes["regular"]
    fBold = fontes["bold"]

    corCabecalho = (0.267, 0.447, 0.769)   # Azul FECORI (#4472C4)
    corZebra = (0.851, 0.882, 0.949)       # Azul claro (#D9E1F2)
    corBranco = (1.0, 1.0, 1.0)
    corPreto = (0.08, 0.08, 0.08)
    corBorda = (0.65, 0.72, 0.85)

    logoBytes = carregarBytesLogoSemFundo(caminhoLogo)
    if logoBytes:
        page.insert_image(fitz.Rect(42, 20, 122, 104), stream=logoBytes, keep_proportion=True)

    _inserirTextoAlinhado(
        page, 130, largura - 130, 56, f"Resultado de Clubes do {edicaoRomanos}", fBold, 20.0, "center", corPreto
    )
    _inserirTextoAlinhado(
        page, 130, largura - 130, 82, "Campeonato Cearense de Orientação", fBold, 20.0, "center", corPreto
    )
    _inserirTextoAlinhado(
        page, largura - 200, largura - 45, 72, "FECORI", fBold, 24.0, "right", (0.15, 0.15, 0.15)
    )

    margemX = 45.0
    topoTabela = 112.0
    alturaCab = 34.0
    clubes = [c for c in resultadoApuracao["classificacaoClubes"] if c["totalPontos"] > 0]
    alturaLinha = min(38.0, float(int((altura - topoTabela - alturaCab - 55) / max(len(clubes), 1))))

    colX = [
        margemX,
        margemX + 60,
        margemX + 235,
        margemX + 290,
        margemX + 355,
        margemX + 435,
        margemX + 515,
        margemX + 595,
        margemX + 675,
        largura - margemX,
    ]
    titulosCol = [
        ("Class.", "center"),
        ("Clube", "left"),
        ("Fed.", "center"),
        ("Atletas", "center"),
        ("1ª Etapa", "right"),
        ("2ª Etapa", "right"),
        ("3ª Etapa", "right"),
        ("4ª Etapa", "right"),
        ("Total Pontos", "right"),
    ]

    rectCab = fitz.Rect(margemX, topoTabela, largura - margemX, topoTabela + alturaCab)
    page.draw_rect(rectCab, color=corCabecalho, fill=corCabecalho)
    yBaseCab = topoTabela + 21.5
    for i, (titulo, alinhamento) in enumerate(titulosCol):
        _inserirTextoAlinhado(page, colX[i] + 6, colX[i + 1] - 6, yBaseCab, titulo, fBold, 12.0, alinhamento, corBranco)

    yAtual = topoTabela + alturaCab
    for idx, c in enumerate(clubes, start=1):
        rectLinha = fitz.Rect(margemX, yAtual, largura - margemX, yAtual + alturaLinha)
        corFundo = corZebra if idx % 2 == 1 else corBranco
        page.draw_rect(rectLinha, color=corBorda, fill=corFundo, width=0.5)

        estLinha = fBold if idx <= 3 else fRegular
        celulas = [
            (f"{idx}º", "center"),
            (c["sigla"], "left"),
            (c.get("federacaoSigla") or "-", "center"),
            (str(c["qtdAtletas"]), "center"),
            (formatarMoedaPontos(c["pontosPorEtapa"].get(1, Decimal("0.00"))), "right"),
            (formatarMoedaPontos(c["pontosPorEtapa"].get(2, Decimal("0.00"))), "right"),
            (formatarMoedaPontos(c["pontosPorEtapa"].get(3, Decimal("0.00"))), "right"),
            (formatarMoedaPontos(c["pontosPorEtapa"].get(4, Decimal("0.00"))), "right"),
            (formatarMoedaPontos(c["totalPontos"]), "right"),
        ]
        yBaseLinha = yAtual + (alturaLinha * 0.64)
        for i, (valor, alinhamento) in enumerate(celulas):
            _inserirTextoAlinhado(
                page, colX[i] + 6, colX[i + 1] - 6, yBaseLinha, valor, estLinha, 12.5, alinhamento, corPreto
            )

        yAtual += alturaLinha

    carimbo = datetime.now().strftime("%d/%m/%Y - %H:%M")
    _inserirTextoAlinhado(page, margemX, 300.0, altura - 18.0, carimbo, fRegular, 9.5, "left", corPreto)
    _inserirTextoAlinhado(
        page,
        largura - 380.0,
        largura - margemX,
        altura - 18.0,
        f"{nomeArquivoPlanilha} - resultadoClubes",
        fRegular,
        9.5,
        "right",
        corPreto,
    )

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaidaPdf)), exist_ok=True)
    doc.save(caminhoSaidaPdf)
    doc.close()
