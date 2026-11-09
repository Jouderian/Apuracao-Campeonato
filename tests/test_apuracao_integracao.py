# -*- coding: utf-8 -*-
"""Testes de integração: apuração completa com dados sintéticos, PDF parcial e utilitários da CLI."""
from decimal import Decimal
import os
import tempfile
import unittest

from src.apurarCampeonato import converterParaRomano, obterEdicaoRomana
from src.motorCalculo.pontuacao import STATUS_OK, apurarCampeonatoCCO
from src.relatorios import geradorExcelPdf
from src.relatorios.geradorExcelPdf import (
    gerarPdfResultadoParcialAtletas,
    gerarPlanilhaExcelApuracao,
)
from src.relatorios.geradorMarkdown import gerarRelatorioIndividualMarkdown

CATEGORIA = "H Adulto A"


def _registro(etapa: int, cbo: int, nome: str, segundos: int) -> dict:
    return {
        "competitionId": 30 + etapa, "runnerPk": cbo * 10 + etapa, "cbo": cbo, "nome": nome, "sexo": 1,
        "clubeId": 1, "clubeSigla": "AAA", "clubeNome": "Clube A",
        "clubeFiliadoCBO": True, "categoriaId": 1, "categoria": CATEGORIA,
        "statusCodigo": STATUS_OK, "statusSigla": "OK", "classifyYN": True,
        "tempo": f"00:{segundos // 60:02d}:{segundos % 60:02d}", "tempoSegundos": segundos,
        "tempoMs": 0, "etapa": etapa,
    }


def montarDadosSinteticos() -> tuple[dict, dict]:
    """Três atletas do mesmo clube em 4 etapas.

    - 1 (Ana): 1ª colocada em todas as etapas.
    - 2 (Beto): 2º nas etapas 1 a 3 e ausente na 4ª.
    - 3 (Caio): 3º nas etapas 1 e 3, 2º na 4ª (Beto ausente) e voluntário na 2ª.
    """
    registros = []
    for etapa in (1, 2, 3, 4):
        registros.append(_registro(etapa, 1, "Ana", 1000))
        if etapa != 4:
            registros.append(_registro(etapa, 2, "Beto", 1100))
        if etapa != 2:
            registros.append(_registro(etapa, 3, "Caio", 1200))
    dadosHelga = {
        "fonte": "Sintetico.mdb",
        "sha256Fonte": "0" * 64,
        "etapas": [{"numeroEtapa": n, "descricao": f"{n}ª etapa"} for n in (1, 2, 3, 4)],
        "clubes": [{
            "clubeId": 1, "sigla": "AAA", "nome": "Clube A", "filiadoCBO": True, "federacaoSigla": "FED",
        }],
        "perfisAtletas": {},
        "registrosEtapas": registros,
    }
    dadosVoluntarios = {
        "voluntarios": [{"etapa": 2, "cbo": 3, "nome": "Caio"}],
        "penalidadesArt23": [],
    }
    return dadosHelga, dadosVoluntarios


class TestApuracaoCompleta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultado = apurarCampeonatoCCO(*montarDadosSinteticos())
        cls.fichas = {f.cbo: f for f in cls.resultado["fichasPorCategoria"][CATEGORIA]}

    def test_classificacao_na_categoria(self):
        self.assertEqual([f.cbo for f in self.resultado["fichasPorCategoria"][CATEGORIA]], [1, 2, 3])
        self.assertEqual([self.fichas[c].colocacaoNaCategoria for c in (1, 2, 3)], [1, 2, 3])

    def test_descarte_remove_a_pior_etapa_de_quem_tem_mais_de_3_etapas(self):
        self.assertEqual(self.fichas[1].pontuacaoTotal, Decimal("120.00"))   # 4 x 40 - 1 descarte
        self.assertEqual(self.fichas[2].pontuacaoTotal, Decimal("111.00"))   # 37 x 3 + 0 (descartado)
        self.assertEqual(self.fichas[2].etapaDescartada, 4)

    def test_voluntario_recebe_media_das_demais_etapas(self):
        etapaVol = self.fichas[3].etapas[2]
        self.assertTrue(etapaVol.atuouComoVoluntario)
        # Demais etapas: 35, 35 e 37. O descarte tira um 35 e a média é (35 + 37) / 2.
        self.assertEqual(etapaVol.pontosFinais, Decimal("36.00"))
        self.assertEqual(self.fichas[3].pontuacaoTotal, Decimal("108.00"))   # 35 + 36 + 37 (um 35 descartado)

    def test_elegibilidade_exige_minimo_de_etapas(self):
        self.assertTrue(self.fichas[1].elegivelPremiacao)
        self.assertTrue(self.fichas[3].elegivelPremiacao)

    def test_pontuacao_do_clube_soma_top_3_por_categoria_e_etapa(self):
        clube = self.resultado["classificacaoClubes"][0]
        self.assertEqual(clube["sigla"], "AAA")
        self.assertEqual(clube["pontosPorEtapa"][1], Decimal("112.00"))   # 40 + 37 + 35
        self.assertEqual(clube["pontosPorEtapa"][2], Decimal("113.00"))   # 40 + 37 + média do voluntário (36)
        self.assertEqual(clube["pontosPorEtapa"][4], Decimal("77.00"))    # 40 + 37 (Beto ausente)
        self.assertEqual(clube["qtdAtletas"], 3)

    def test_voluntarios_pendentes_sao_informados(self):
        self.assertEqual(self.resultado["etapasComVoluntarios"], [2])

    def test_unificacao_cbo_provisorio_consolida_atleta_e_clube(self):
        dadosHelga, dadosVoluntarios = montarDadosSinteticos()
        regProv = _registro(2, 990004, "Samilla", 1300)
        regProv.update({"clubeId": 361, "clubeSigla": "Individual", "clubeNome": "Individual", "clubeFiliadoCBO": False})
        regOfic = _registro(3, 24219, "Samilla", 1300)
        dadosHelga["registrosEtapas"].extend([regProv, regOfic])
        dadosHelga["perfisAtletas"]["24219"] = {
            "cbo": 24219, "nome": "Samilla", "clubeId": 1, "clubeSigla": "AAA",
            "clubeNome": "Clube A", "clubeFiliadoCBO": True,
        }
        dadosVoluntarios["unificacoesCbo"] = [{"cboProvisorio": 990004, "cboOficial": 24219, "nome": "Samilla"}]

        res = apurarCampeonatoCCO(dadosHelga, dadosVoluntarios)
        fichas = {f.cbo: f for f in res["fichasPorCategoria"][CATEGORIA]}
        self.assertNotIn(990004, fichas)
        self.assertIn(24219, fichas)
        fichaSamilla = fichas[24219]
        self.assertEqual(fichaSamilla.clubeSigla, "AAA")
        self.assertEqual(fichaSamilla.etapasParticipadas, 2)
        self.assertTrue(fichaSamilla.elegivelPremiacao)
        self.assertFalse(fichaSamilla.competiuEmMultiplasCategorias)
        self.assertEqual(fichaSamilla.pontuacaoTotal, Decimal("68.00"))   # 35 (3ª na 2ª et.) + 33 (4ª na 3ª et.)

    def test_relatorio_individual_markdown_italico_voluntario_e_legenda_unificada(self):
        md = gerarRelatorioIndividualMarkdown(2026, "XX CCO", self.resultado)
        # Caio (CBO 3) teve média de voluntário de 36,00 na 2ª etapa: deve estar em itálico e sem '(VOL)'
        self.assertIn("*36,00*", md)
        self.assertNotIn("(VOL)", md)
        # Informações unificadas no cabeçalho inicial e sem seção de legenda ao final
        self.assertNotIn("## Legenda", md)
        self.assertIn("valores tachados", md)
        self.assertIn("valores em itálico", md)



class TestPdfParcial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resultado = apurarCampeonatoCCO(*montarDadosSinteticos())
        cls.pasta = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.pasta.cleanup)

        from PIL import Image

        cls.caminhoLogo = os.path.join(cls.pasta.name, "logo.png")
        Image.new("RGB", (40, 40), (200, 30, 30)).save(cls.caminhoLogo)

    def _gerar(self, nome: str, logo: str | None):
        caminho = os.path.join(self.pasta.name, nome)
        gerarPdfResultadoParcialAtletas(2026, "XX", self.resultado, [caminho], caminhoLogo=logo)
        import pymupdf as fitz

        doc = fitz.open(caminho)
        self.addCleanup(doc.close)
        return doc[0]

    def test_sem_logo_nao_ha_imagem_e_titulo_comeca_na_margem(self):
        pagina = self._gerar("semLogo.pdf", None)
        self.assertEqual(len(pagina.get_images()), 0)
        primeira = next(w for w in pagina.get_text("words") if w[4] == "Resultado")
        self.assertAlmostEqual(primeira[0], geradorExcelPdf.X_ESQ, delta=0.5)

    def test_nao_oficial_fica_alinhado_a_direita_da_folha(self):
        pagina = self._gerar("direita.pdf", None)
        palavras = {w[4]: w for w in pagina.get_text("words")}
        self.assertAlmostEqual(palavras["OFICIAL"][2], geradorExcelPdf.X_DIR, delta=0.5)
        titulo = palavras["Orientação"]
        self.assertLess(titulo[2], palavras["NÃO"][0])   # título termina antes do aviso, que não o segue colado
        self.assertGreater(palavras["NÃO"][0] - titulo[2], 50)

    def test_com_logo_insere_a_imagem(self):
        pagina = self._gerar("comLogo.pdf", self.caminhoLogo)
        self.assertEqual(len(pagina.get_images()), 1)

    def test_descarte_destacado_com_traco_tachado_e_avisos_no_pdf(self):
        caminho = os.path.join(self.pasta.name, "descarte.pdf")
        gerarPdfResultadoParcialAtletas(2026, "XX", self.resultado, [caminho], caminhoLogo=None)
        import pymupdf as fitz

        doc = fitz.open(caminho)
        self.addCleanup(doc.close)

        # Rodapé não deve conter o texto de descarte
        for pag in doc:
            textoPag = pag.get_text("text").replace("\xa0", " ")
            self.assertNotIn("descarte da pontuação mais baixa", textoPag.split("\n")[-3:])

        # No Linux a fonte alternativa devolve o marcador "\u2022" como "\u00b7" na extra\u00e7\u00e3o de texto.
        ultimaPagTexto = (
            doc[-1].get_text("text").replace("\xa0", " ").replace("\u2010", "-").replace("\u00b7", "\u2022")
        )
        self.assertNotIn("DESCARTE:", ultimaPagTexto)
        self.assertIn("OBSERVAÇÕES:", ultimaPagTexto)
        self.assertIn(
            "• O valor total já considera o descarte da pontuação mais baixa, conforme "
            "estabelecido no Art. 34 do Regulamento. A etapa descartada encontra-se "
            "destacada em cinza e com o texto riscado.",
            ultimaPagTexto.replace("\n", " "),
        )
        self.assertIn(
            "• Este resultado não é oficial e ainda não inclui os voluntários",
            ultimaPagTexto.replace("\n", " "),
        )
        self.assertIn(
            "• Caso identifique alguma inconformidade, envie um eMail para",
            ultimaPagTexto.replace("\n", " "),
        )

        desenhosDescarte = [
            d for pag in doc for d in pag.get_drawings()
            if d.get("color") and abs(d["color"][0] - geradorExcelPdf.COR_DESCARTE_LINHA[0]) < 0.01
        ]
        self.assertGreater(len(desenhosDescarte), 0)

        desenhosAmarelos = [
            d for pag in doc for d in pag.get_drawings()
            if d.get("fill") and all(abs(c1 - c2) < 0.01 for c1, c2 in zip(d["fill"], geradorExcelPdf.COR_AMARELO_FUNDO, strict=False))
        ]
        self.assertGreater(len(desenhosAmarelos), 0)

    def test_planilha_excel_e_gerada_com_as_quatro_abas(self):
        caminho = os.path.join(self.pasta.name, "apuracao.xlsx")
        gerarPlanilhaExcelApuracao(2026, "XX CCO", "XX", self.resultado, caminho)
        from openpyxl import load_workbook

        wb = load_workbook(caminho)
        self.assertEqual(
            wb.sheetnames,
            ["resultadoParcial", "resultadoClubes", "resultadoIndividual", "memoriaClubesTop3"],
        )
        wsParcial = wb["resultadoParcial"]
        # Caio (CBO 3) foi voluntário na 2ª etapa (coluna 7) -> célula em amarelo (FFFF00)
        linhaCaio = None
        for r in range(4, wsParcial.max_row):
            if wsParcial.cell(row=r, column=3).value == 3:
                linhaCaio = r
                break
        self.assertIsNotNone(linhaCaio)
        celulaVol = wsParcial.cell(row=linhaCaio, column=7)
        self.assertIsNotNone(celulaVol.fill)
        self.assertIn("FFFF00", str(celulaVol.fill.start_color.rgb))


class TestEdicaoRomana(unittest.TestCase):
    def test_conversao_para_romano(self):
        self.assertEqual(converterParaRomano(4), "IV")
        self.assertEqual(converterParaRomano(19), "XIX")
        self.assertEqual(converterParaRomano(49), "XLIX")
        with self.assertRaises(ValueError):
            converterParaRomano(0)

    def test_edicao_a_partir_do_ano(self):
        self.assertEqual(obterEdicaoRomana(2025), "XIX")
        self.assertEqual(obterEdicaoRomana(2026), "XX")
        self.assertEqual(obterEdicaoRomana(2040), "XXXIV")


if __name__ == "__main__":
    unittest.main()
