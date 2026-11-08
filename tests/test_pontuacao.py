# -*- coding: utf-8 -*-
"""Testes unitários do motor de cálculo de pontuação (Regulamento Arts. 23, 31, 33, 34 e 35)."""
from decimal import Decimal
import unittest

from src.motorCalculo.pontuacao import (
    calcularMediaVoluntarioCCO,
    calcularPontosEtapa,
    calcularPontuacaoClubeNaEtapa,
    ehCategoriaSemPontuacao,
    exigirMinimoEtapasVoluntarioCCO,
    selecionarIndiceDescarte,
    temDireitoDescarteCCO,
)


class TestPontuacaoEtapa(unittest.TestCase):
    def test_primeiros_26_colocados(self):
        self.assertEqual(calcularPontosEtapa('H21E', True, 1), 40)
        self.assertEqual(calcularPontosEtapa('H21E', True, 2), 37)
        self.assertEqual(calcularPontosEtapa('H21E', True, 3), 35)
        self.assertEqual(calcularPontosEtapa('H21E', True, 4), 33)
        self.assertEqual(calcularPontosEtapa('H21E', True, 26), 11)

    def test_a_partir_do_27_colocado_recebe_10_pontos(self):
        self.assertEqual(calcularPontosEtapa('H21A', True, 27), 10)
        self.assertEqual(calcularPontosEtapa('H21A', True, 50), 10)

    def test_nao_classificado_ou_percurso_anulado_recebe_1_ponto(self):
        self.assertEqual(calcularPontosEtapa('D21E', False, None), 1)
        self.assertEqual(calcularPontosEtapa('D21E', True, 1, percursoAnulado=True), 1)

    def test_categorias_acompanhadas_e_abertas_nao_pontuam(self):
        for cat in ('HN1', 'DN2', 'Acompanhado Adulto', 'Aberto Curto'):
            self.assertTrue(ehCategoriaSemPontuacao(cat))
            self.assertEqual(calcularPontosEtapa(cat, True, 1), 0)


class TestDescarteEVoluntarios(unittest.TestCase):
    def test_direito_descarte_cco_apenas_mais_de_3_etapas(self):
        self.assertFalse(temDireitoDescarteCCO(2))
        self.assertFalse(temDireitoDescarteCCO(3))
        self.assertTrue(temDireitoDescarteCCO(4))

    def test_penalidade_art23_impede_descarte_daquela_etapa(self):
        notas = [
            (Decimal('1'), False),   # Etapa 1: penalizado pelo Art. 23 (não pode descartar)
            (Decimal('35'), True),   # Etapa 2
            (Decimal('40'), True),   # Etapa 3
            (Decimal('37'), True),   # Etapa 4
        ]
        self.assertEqual(selecionarIndiceDescarte(notas), 1)

    def test_minimo_etapas_voluntario_arredonda_para_baixo(self):
        self.assertEqual(exigirMinimoEtapasVoluntarioCCO(4), 2)
        self.assertEqual(exigirMinimoEtapasVoluntarioCCO(5), 2)
        self.assertEqual(exigirMinimoEtapasVoluntarioCCO(3), 1)

    def test_media_voluntario_cco_aplica_descarte_antes_da_media(self):
        # Campeonato de 4 etapas (>3, logo tem descarte).
        # Atleta atuou como voluntário na 1ª etapa e se inscreveu nas etapas 2, 3 e 4,
        # obtendo 40, 35 e 10 pontos. Descarta-se 10; média entre 40 e 35 = 37.50.
        media = calcularMediaVoluntarioCCO(
            etapasRealizadasNoCampeonato=4,
            resultadosInscritosExcetoVoluntario=[(40, True), (35, True), (10, True)],
            participouEtapasTotais=3,
        )
        self.assertEqual(media, Decimal('37.50'))


class TestPontuacaoClubes(unittest.TestCase):
    def test_soma_top_3_atletas_filiados_por_categoria(self):
        pontosPorCategoria = {
            'H21E': [
                (Decimal('40'), True),
                (Decimal('37'), True),
                (Decimal('35'), False),  # Não filiado à CBO: ignorado para o clube
                (Decimal('33'), True),
                (Decimal('32'), True),   # 4º filiado: excede o limite de 3 da categoria
            ],
            'D21E': [
                (Decimal('40'), True),
                (Decimal('35'), True),
            ],
        }
        # H21E soma 40 + 37 + 33 = 110; D21E soma 40 + 35 = 75 -> Total = 185.00
        total = calcularPontuacaoClubeNaEtapa(pontosPorCategoria, clubeFiliadoCBO=True)
        self.assertEqual(total, Decimal('185.00'))

    def test_clube_nao_filiado_nao_pontua(self):
        pontosPorCategoria = {'H21E': [(Decimal('40'), True)]}
        self.assertEqual(
            calcularPontuacaoClubeNaEtapa(pontosPorCategoria, clubeFiliadoCBO=False),
            Decimal('0.00'),
        )


if __name__ == '__main__':
    unittest.main()

