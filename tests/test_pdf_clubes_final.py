# -*- coding: utf-8 -*-
"""Testes do PDF do Resultado de Clubes final (layout da FECORI) e da busca dos brasões."""
import os
import tempfile
import unittest

import pymupdf as fitz
from PIL import Image

from src.motorCalculo.pontuacao import apurarCampeonatoCCO
from src.motorCalculo.regulamentos import REGRAS_CCO_2025
from src.relatorios.geradorPdfClubesFinal import gerarPdfResultadoClubes, localizarBrasoes, nomeArquivoBrasao
from tests.test_apuracao_integracao import montarDadosSinteticos


class TestBrasoes(unittest.TestCase):
    def test_nome_do_arquivo_do_brasao(self):
        self.assertEqual(nomeArquivoBrasao("COFORT"), "cofort")
        self.assertEqual(nomeArquivoBrasao("COqueiro"), "coqueiro")
        self.assertEqual(nomeArquivoBrasao("TRILHA NORTE"), "trilhaNorte")
        self.assertEqual(nomeArquivoBrasao("10º D SUP"), "10oDSup")
        self.assertEqual(nomeArquivoBrasao("..."), "")

    def test_localiza_so_os_brasoes_que_existem(self):
        with tempfile.TemporaryDirectory() as pasta:
            Image.new("RGB", (10, 10), (200, 0, 0)).save(os.path.join(pasta, "trilhaNorte.png"))
            Image.new("RGB", (10, 10), (0, 0, 200)).save(os.path.join(pasta, "cofort.jpg"))
            achados = localizarBrasoes(["TRILHA NORTE", "COFORT", "COCAP"], pasta)
        self.assertEqual(sorted(achados), ["COFORT", "TRILHA NORTE"])
        self.assertTrue(achados["COFORT"].endswith("cofort.jpg"))


class TestPdfClubes(unittest.TestCase):
    def _gerar(self, brasoes, logoFecori=None):
        resultado = apurarCampeonatoCCO(*montarDadosSinteticos(), REGRAS_CCO_2025)
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "clubes.pdf")
            gerarPdfResultadoClubes(2025, "XIX", resultado, caminho, "apuracaoCampeonato2025.xlsx", None, logoFecori, brasoes)
            doc = fitz.open(caminho)
            pagina = doc[0]
            texto = pagina.get_text("text").replace("\xa0", " ").replace("‐", "-").replace("\n", " ")
            imagens = len(pagina.get_images())
            paginas, retangulo = len(doc), pagina.rect
            doc.close()
        return texto, imagens, paginas, retangulo, resultado

    def test_layout_de_cinco_colunas_em_uma_pagina_paisagem(self):
        texto, imagens, paginas, retangulo, resultado = self._gerar({})
        self.assertEqual(paginas, 1)
        self.assertGreater(retangulo.width, retangulo.height)
        self.assertIn("Resultado de Clubes do XIX Campeonato Cearense de Orientação", texto)
        for coluna in ("Class.", "Brasão", "Clube", "Atletas", "Total Pontos"):
            self.assertIn(coluna, texto)
        for ausente in ("Fed.", "Etapa"):
            self.assertNotIn(ausente, texto)
        self.assertIn("AAA", texto)
        self.assertIn(f"{resultado['classificacaoClubes'][0]['totalPontos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), texto)
        self.assertIn("apuracaoCampeonato2025.xlsx - resultadoClubes", texto)
        self.assertEqual(imagens, 0)

    def test_brasao_e_logo_da_fecori_entram_como_imagens(self):
        with tempfile.TemporaryDirectory() as pasta:
            brasao = os.path.join(pasta, "aaa.png")
            fecori = os.path.join(pasta, "fecori.png")
            Image.new("RGB", (40, 60), (200, 0, 0)).save(brasao)
            Image.new("RGB", (120, 30), (0, 0, 120)).save(fecori)
            _, imagens, _, _, _ = self._gerar({"AAA": brasao}, fecori)
        self.assertEqual(imagens, 2)   # brasão do clube e logo da FECORI


if __name__ == "__main__":
    unittest.main()
