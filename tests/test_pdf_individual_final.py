# -*- coding: utf-8 -*-
"""Testes do PDF do Resultado Individual final (layout da FECORI)."""
from decimal import Decimal
import os
import tempfile
import unittest

import pymupdf as fitz

from src.motorCalculo.pontuacao import (
    ClassificacaoAtletaCategoria,
    DesempenhoEtapaCalculado,
    apurarCampeonatoCCO,
)
from src.motorCalculo.regulamentos import REGRAS_CCO_2025, REGRAS_CCO_2026
from src.relatorios.geradorPdfIndividualFinal import (
    ORDEM_CATEGORIAS,
    _paginar,
    classificarPremio,
    estiloDaCelula,
    formatarPontos,
    gerarPdfResultadoIndividualFinal,
    ordenarCategorias,
    rotuloArtigo,
)
from tests.test_apuracao_integracao import montarDadosSinteticos


def _ficha(categoria="H Adulto A", cbo=1, final=0, naCategoria=0, total="40", elegivel=True) -> ClassificacaoAtletaCategoria:
    ficha = ClassificacaoAtletaCategoria(
        cbo=cbo, nome=f"Atleta {cbo}", clubeId=1, clubeSigla="AAA", clubeNome="Clube A", clubeFiliadoCBO=True,
        categoria=categoria,
    )
    ficha.colocacaoFinal, ficha.colocacaoNaCategoria = final, naCategoria
    ficha.pontuacaoTotal, ficha.elegivelPremiacao = Decimal(total), elegivel
    return ficha


def _etapa(**campos) -> DesempenhoEtapaCalculado:
    base = {"etapa": 1, "inscrito": True, "participou": True, "statusSigla": "OK", "colocacao": 3,
            "pontosFinais": Decimal("35")}
    base.update(campos)
    return DesempenhoEtapaCalculado(**base)


class TestRegrasDoLayout(unittest.TestCase):
    def test_ordem_das_categorias_segue_a_fecori_e_as_nao_previstas_vao_ao_fim(self):
        embaralhadas = ["H Infant N", "D Adulto E", "Categoria Nova", "H Vet A", "D Adulto E2"]
        self.assertEqual(ordenarCategorias(embaralhadas), ["D Adulto E", "H Vet A", "H Infant N", "Categoria Nova", "D Adulto E2"])
        self.assertEqual(len(ORDEM_CATEGORIAS), len(set(ORDEM_CATEGORIAS)))

    def test_rotulo_do_artigo_para_a_legenda(self):
        self.assertEqual(rotuloArtigo("Art. 42, § 1º"), "Art.42 §1°")
        self.assertEqual(rotuloArtigo("Art. 36"), "Art.36")
        self.assertEqual(rotuloArtigo("Art. 20, Parágrafo Único"), "Art.20")

    def test_pontos_com_duas_casas_e_virgula(self):
        self.assertEqual(formatarPontos(Decimal("22.3333333")), "22,33")
        self.assertEqual(formatarPontos(Decimal("40")), "40,00")
        self.assertEqual(formatarPontos(Decimal("17.5")), "17,50")


class TestPremiacao(unittest.TestCase):
    def test_ouro_para_todo_campeao_inclusive_novato_prata_e_bronze(self):
        self.assertEqual(classificarPremio(_ficha(final=1, naCategoria=1)), "ouro")
        self.assertEqual(classificarPremio(_ficha("D Vet N", final=1, naCategoria=1)), "ouro")
        self.assertEqual(classificarPremio(_ficha(final=2, naCategoria=2)), "prata")
        self.assertEqual(classificarPremio(_ficha(final=3, naCategoria=3)), "bronze")
        self.assertIsNone(classificarPremio(_ficha(final=4, naCategoria=4)))

    def test_pododio_sem_participacao_minima_recebe_o_rotulo_do_art42(self):
        self.assertEqual(classificarPremio(_ficha(final=3, naCategoria=3, elegivel=False)), "art42")

    def test_rotulo_do_art42_segue_a_posicao_na_categoria_mesmo_sem_colocacao_final(self):
        # Categoria que perde pela troca de categoria (colocação final 0), mas 2º na categoria, com pontos.
        self.assertEqual(classificarPremio(_ficha("H Master N", final=0, naCategoria=2, total="1", elegivel=False)), "art42")

    def test_sem_pontos_nao_ha_premiacao_nem_rotulo(self):
        self.assertIsNone(classificarPremio(_ficha(final=0, naCategoria=2, total="0", elegivel=False)))


class TestCelulaDeEtapa(unittest.TestCase):
    def test_estilos(self):
        self.assertEqual(estiloDaCelula(_etapa()), ("35,00", "normal"))
        self.assertEqual(estiloDaCelula(_etapa(inscrito=False, colocacao=None, statusSigla="-", pontosFinais=Decimal("0"))), ("", "vazio"))
        self.assertEqual(estiloDaCelula(_etapa(colocacao=None, statusSigla="NP", pontosFinais=Decimal("0"))), ("-", "traco"))
        self.assertEqual(estiloDaCelula(_etapa(colocacao=None, statusSigla="NC", pontosFinais=Decimal("1"))), ("1,00", "naoClassificado"))
        self.assertEqual(estiloDaCelula(_etapa(atuouComoVoluntario=True, colocacao=None, pontosFinais=Decimal("22.3333"))), ("22,33", "media"))
        self.assertEqual(estiloDaCelula(_etapa(atuouComoVoluntario=True, colocacao=None, pontosFinais=Decimal("0"))), ("-", "media"))
        self.assertEqual(estiloDaCelula(_etapa(descartada=True)), ("35,00", "descartada"))

    def test_celula_ajustada_pelo_publicado(self):
        ajustada = dict(ajustadoOficial=True, colocacao=None)
        self.assertEqual(estiloDaCelula(_etapa(**ajustada, pontosFinais=Decimal("17.5"), destaqueMedia=True, inscrito=False)), ("17,50", "media"))
        self.assertEqual(estiloDaCelula(_etapa(**ajustada, pontosFinais=Decimal("21"))), ("21,00", "normal"))
        self.assertEqual(estiloDaCelula(_etapa(**ajustada, pontosFinais=Decimal("0"))), ("-", "traco"))
        self.assertEqual(estiloDaCelula(_etapa(**ajustada, pontosFinais=Decimal("0"), inscrito=False)), ("", "vazio"))


class TestPaginacao(unittest.TestCase):
    def _categoria(self, nome, n):
        return nome, [_ficha(nome, cbo=i) for i in range(n)]

    def test_categoria_que_nao_cabe_na_pagina_vai_inteira_para_a_seguinte(self):
        paginas = _paginar([self._categoria("A", 20), self._categoria("B", 9), self._categoria("C", 5)], 23, 27)
        self.assertEqual([len(p) for p in paginas], [20, 14])   # B (9) não cabe nos 3 lugares restantes
        self.assertEqual({f.categoria for f, _ in paginas[1]}, {"B", "C"})

    def test_a_ultima_linha_de_cada_categoria_fecha_o_bloco(self):
        paginas = _paginar([self._categoria("A", 3), self._categoria("B", 2)], 23, 27)
        self.assertEqual([ultima for _, ultima in paginas[0]], [False, False, True, False, True])

    def test_categoria_maior_que_a_pagina_e_dividida(self):
        paginas = _paginar([self._categoria("A", 60)], 23, 27)
        self.assertEqual([len(p) for p in paginas], [23, 27, 10])


class TestPdfGerado(unittest.TestCase):
    def _gerar(self, regras, edicao):
        dadosHelga, dadosVol = montarDadosSinteticos()
        resultado = apurarCampeonatoCCO(dadosHelga, dadosVol, regras)
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "individual.pdf")
            gerarPdfResultadoIndividualFinal(2025, edicao, resultado, caminho, caminhoLogo=None)
            doc = fitz.open(caminho)
            paginas = [p.get_text("text").replace("\xa0", " ").replace("‐", "-").replace("\n", " ") for p in doc]
            retrato = doc[0].rect
            doc.close()
        return paginas, retrato

    def test_pdf_2025_em_paisagem_com_titulo_tabela_e_legenda_do_ano(self):
        paginas, retangulo = self._gerar(REGRAS_CCO_2025, "XIX")
        self.assertGreater(retangulo.width, retangulo.height)   # A4 paisagem
        texto = " ".join(paginas)
        self.assertIn("Resultado Individual do", paginas[0])
        self.assertIn("XIX Campeonato Cearense de Orientação", paginas[0])
        for coluna in ("Categoria", "Class.", "1ª etapa", "4ª etapa", "Total", "Premiação"):
            self.assertIn(coluna, paginas[0])
        for item in ("Legenda", "Art.20 - Abandono da competição", "Art.36 - Pontuação por média",
                     "Art.42 §1° - Participação mínima"):
            self.assertIn(item, paginas[-1])
        for proibido in ("NÃO OFICIAL", "parcial", "OBSERVAÇÕES"):
            self.assertNotIn(proibido, texto)
        self.assertIn(f"1 / {len(paginas)}", paginas[0])

    def test_legenda_cita_os_artigos_do_regulamento_do_ano(self):
        paginas, _ = self._gerar(REGRAS_CCO_2026, "XX")
        self.assertIn("Art.33 - Pontuação por média", paginas[-1])
        self.assertIn("Art.39 §1° - Participação mínima", paginas[-1])
        self.assertIn("Art.31 §2° - Atleta não classificado", paginas[-1])


if __name__ == "__main__":
    unittest.main()
