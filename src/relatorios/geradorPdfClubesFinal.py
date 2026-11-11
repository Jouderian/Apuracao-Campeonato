# -*- coding: utf-8 -*-
"""PDF do Resultado de Clubes final, no layout publicado pela FECORI (A4 paisagem).

Cinco colunas (Class., Brasão, Clube, Atletas, Total Pontos), uma linha por clube classificado, brasão do clube,
logo da edição à esquerda e logo da FECORI à direita do título. As medidas vêm do PDF oficial de 2025.
"""
import os
import re
import unicodedata
from datetime import datetime
from typing import Any

from src.relatorios.geradorExcelPdf import _inserirTextoAlinhado, _obterMapaFontesPdf, carregarBytesLogoSemFundo
from src.relatorios.geradorMarkdown import formatarMoedaPontos

Cor = tuple[float, float, float]

LARGURA, ALTURA = 841.92, 595.32
X_TABELA_ESQ, X_TABELA_DIR = 30.6, 811.1
Y_CABECALHO, ALT_CABECALHO = 161.9, 39.2
Y_CORPO_FIM, ALT_LINHA_PADRAO = 518.6, 45.37
X_CLASS_CENTRO, X_BRASAO_CENTRO, X_CLUBE, X_ATLETAS_CENTRO, X_TOTAL_DIR = 110.9, 268.4, 349.3, 605.3, 796.8
X_CLUBE_CABECALHO, X_ATLETAS_CABECALHO, X_TOTAL_CABECALHO = 358.9, 599.5, 800.6
CAIXA_BRASAO = (244.0, 294.0)   # faixa horizontal (x0, x1) reservada ao brasão em cada linha

AZUL: Cor = (0.267, 0.447, 0.769)
AZUL_CLARO: Cor = (0.851, 0.882, 0.949)
AZUL_BORDA: Cor = (0.557, 0.663, 0.859)
BRANCO: Cor = (1.0, 1.0, 1.0)
PRETO: Cor = (0.0, 0.0, 0.0)

EXTENSOES_BRASAO = (".png", ".jpg", ".jpeg")


def nomeArquivoBrasao(sigla: str) -> str:
    """Nome do arquivo do brasão de um clube em `Dados/brasoes/`: sigla sem acento em camelCase (`trilhaNorte`)."""
    semAcento = unicodedata.normalize("NFKD", sigla).encode("ascii", "ignore").decode()
    partes = [p for p in re.split(r"[^A-Za-z0-9]+", semAcento) if p]
    return (partes[0].lower() + "".join(p.capitalize() for p in partes[1:])) if partes else ""


def localizarBrasoes(siglas: list[str], pastaBrasoes: str) -> dict[str, str]:
    """Mapeia cada sigla de clube ao arquivo do brasão em `pastaBrasoes`, quando existir."""
    encontrados: dict[str, str] = {}
    for sigla in siglas:
        for extensao in EXTENSOES_BRASAO:
            caminho = os.path.join(pastaBrasoes, nomeArquivoBrasao(sigla) + extensao)
            if nomeArquivoBrasao(sigla) and os.path.isfile(caminho):
                encontrados[sigla] = caminho
                break
    return encontrados


def _fonteDoTitulo() -> tuple[str, str | None, Any]:
    """Verdana Bold, como no PDF oficial, ou Helvetica Bold se a fonte não estiver instalada."""
    import pymupdf as fitz

    caminho = r"C:\Windows\Fonts\verdanab.ttf"
    if os.path.isfile(caminho):
        return ("verdanab", caminho, fitz.Font(fontfile=caminho))
    return ("hebo", None, fitz.Font(fontname="hebo"))


def gerarPdfResultadoClubes(
    ano: int,
    edicaoRomanos: str,
    resultadoApuracao: dict[str, Any],
    caminhoSaidaPdf: str,
    nomeArquivoPlanilha: str,
    caminhoLogo: str | None = None,
    caminhoLogoFecori: str | None = None,
    brasoes: dict[str, str] | None = None,
) -> None:
    """Gera o PDF de Resultado de Clubes no layout da FECORI; logos e brasões entram quando os arquivos existem."""
    import pymupdf as fitz

    fontes = _obterMapaFontesPdf()
    regular, negrito = fontes["regular"], fontes["bold"]
    titulo = _fonteDoTitulo()
    clubes = [c for c in resultadoApuracao["classificacaoClubes"] if c["totalPontos"] > 0]

    doc = fitz.open()
    page = doc.new_page(width=LARGURA, height=ALTURA)

    logoBytes = carregarBytesLogoSemFundo(caminhoLogo)
    if logoBytes:
        page.insert_image(fitz.Rect(30.2, 77.0, 112.0, 160.6), stream=logoBytes, keep_proportion=True)
    if caminhoLogoFecori and os.path.isfile(caminhoLogoFecori):
        page.insert_image(fitz.Rect(685.4, 105.1, 810.7, 133.2), filename=caminhoLogoFecori, keep_proportion=True)
    else:
        _inserirTextoAlinhado(page, 650.0, 810.7, 130.0, "FECORI", negrito, 24.0, "right", (0.15, 0.15, 0.15))
    _inserirTextoAlinhado(page, 0.0, LARGURA, 113.8, f"Resultado de Clubes do {edicaoRomanos}", titulo, 20.9, "center", PRETO)
    _inserirTextoAlinhado(page, 0.0, LARGURA, 139.8, "Campeonato Cearense de Orientação", titulo, 20.9, "center", PRETO)

    # Cabeçalho
    page.draw_rect(fitz.Rect(X_TABELA_ESQ, Y_CABECALHO, X_TABELA_DIR, Y_CABECALHO + ALT_CABECALHO), color=None, fill=AZUL)
    yG, yP = Y_CABECALHO + 30.2, Y_CABECALHO + 27.2
    _inserirTextoAlinhado(page, X_CLASS_CENTRO - 60, X_CLASS_CENTRO + 60, yG, "Class.", negrito, 31.3, "center", BRANCO)
    _inserirTextoAlinhado(page, X_BRASAO_CENTRO - 70, X_BRASAO_CENTRO + 70, yG, "Brasão", negrito, 31.3, "center", BRANCO)
    _inserirTextoAlinhado(page, X_CLUBE_CABECALHO, X_CLUBE_CABECALHO + 150, yG, "Clube", negrito, 31.3, "left", BRANCO)
    _inserirTextoAlinhado(page, X_ATLETAS_CABECALHO - 50, X_ATLETAS_CABECALHO + 50, yP, "Atletas", negrito, 22.6,
                          "center", BRANCO)
    _inserirTextoAlinhado(page, X_TOTAL_CABECALHO - 150, X_TOTAL_CABECALHO, yP, "Total Pontos", negrito, 22.6, "right",
                          BRANCO)

    # Linhas (46 pt cada; com muitos clubes a tabela mantém a altura e as linhas encolhem junto com o texto)
    topoCorpo = Y_CABECALHO + ALT_CABECALHO
    altLinha = min(ALT_LINHA_PADRAO, (Y_CORPO_FIM - topoCorpo) / max(len(clubes), 1))
    escala = altLinha / ALT_LINHA_PADRAO
    corpo = 31.3 * escala
    for indice, clube in enumerate(clubes):
        topo = topoCorpo + indice * altLinha
        page.draw_rect(fitz.Rect(X_TABELA_ESQ, topo, X_TABELA_DIR, topo + altLinha), color=None,
                       fill=AZUL_CLARO if indice % 2 == 0 else BRANCO)
        page.draw_line(fitz.Point(X_TABELA_ESQ, topo + altLinha), fitz.Point(X_TABELA_DIR, topo + altLinha),
                       color=AZUL_BORDA, width=0.8)
        y = topo + 33.4 * escala
        _inserirTextoAlinhado(page, X_CLASS_CENTRO - 40, X_CLASS_CENTRO + 40, y, f"{indice + 1}º", regular, corpo,
                              "center", PRETO)
        _inserirTextoAlinhado(page, X_CLUBE, X_CLUBE + 220, y, clube["sigla"], regular, corpo, "left", PRETO)
        _inserirTextoAlinhado(page, X_ATLETAS_CENTRO - 40, X_ATLETAS_CENTRO + 40, y, str(clube["qtdAtletas"]), regular,
                              corpo, "center", PRETO)
        _inserirTextoAlinhado(page, X_TOTAL_DIR - 150, X_TOTAL_DIR, y, formatarMoedaPontos(clube["totalPontos"]), regular,
                              corpo, "right", PRETO)
        caminhoBrasao = (brasoes or {}).get(clube["sigla"])
        if caminhoBrasao and os.path.isfile(caminhoBrasao):
            page.insert_image(
                fitz.Rect(CAIXA_BRASAO[0], topo + 1.2 * escala, CAIXA_BRASAO[1], topo + altLinha - 0.4 * escala),
                filename=caminhoBrasao, keep_proportion=True,
            )
    fimTabela = topoCorpo + len(clubes) * altLinha
    page.draw_rect(fitz.Rect(X_TABELA_ESQ, Y_CABECALHO - 0.4, X_TABELA_DIR, fimTabela + 0.4), color=AZUL_BORDA, width=0.8)

    carimbo = datetime.now().strftime("%d/%m/%Y - %H:%M")
    _inserirTextoAlinhado(page, 29.4, 300.0, 576.8, carimbo, regular, 9.6, "left", PRETO)
    _inserirTextoAlinhado(page, 500.0, 812.7, 576.8, f"{nomeArquivoPlanilha} - resultadoClubes", regular, 9.6, "right",
                          PRETO)

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaidaPdf)), exist_ok=True)
    doc.save(caminhoSaidaPdf)
    doc.close()
