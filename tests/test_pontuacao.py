# -*- coding: utf-8 -*-
"""Testes unitários do motor de cálculo de pontuação (regulamentos 2026: Arts. 23, 31 a 35 e 39; 2025: Arts. 34 a 42)."""
from decimal import Decimal
import unittest

from src.extracaoAccess.leitorVoluntarios import lerVoluntariosMarkdown
from src.motorCalculo.pontuacao import (
    STATUS_CC,
    STATUS_NC,
    STATUS_NP,
    STATUS_OK,
    STATUS_OT,
    calcularMediaVoluntarioCCO,
    calcularPontosEtapa,
    calcularPontosStatusHelga,
    calcularPontuacaoClubeNaEtapa,
    ehCategoriaSemPontuacao,
    normalizarCategoriaPadraoCBO,
    selecionarIndiceDescarte,
    temDireitoDescarteCCO,
)
from src.motorCalculo.regulamentos import REGRAS_CCO_2026, calcularMinimoMetadeEtapas
from src.relatorios.geradorExcelPdf import (
    formatarPontoTabelaParcial,
    sanitizarCelulaExcel,
)


REGRAS = REGRAS_CCO_2026


class TestPontuacaoEtapa(unittest.TestCase):
    def test_primeiros_26_colocados(self):
        self.assertEqual(calcularPontosEtapa('H21E', True, 1, regras=REGRAS), 40)
        self.assertEqual(calcularPontosEtapa('H21E', True, 2, regras=REGRAS), 37)
        self.assertEqual(calcularPontosEtapa('H21E', True, 3, regras=REGRAS), 35)
        self.assertEqual(calcularPontosEtapa('H21E', True, 4, regras=REGRAS), 33)
        self.assertEqual(calcularPontosEtapa('H21E', True, 26, regras=REGRAS), 11)

    def test_a_partir_do_27_colocado_recebe_10_pontos(self):
        self.assertEqual(calcularPontosEtapa('H21A', True, 27, regras=REGRAS), 10)
        self.assertEqual(calcularPontosEtapa('H21A', True, 50, regras=REGRAS), 10)

    def test_nao_classificado_ou_percurso_anulado_recebe_1_ponto(self):
        self.assertEqual(calcularPontosEtapa('D21E', False, None, regras=REGRAS), 1)
        self.assertEqual(calcularPontosEtapa('D21E', True, 1, percursoAnulado=True, regras=REGRAS), 1)

    def test_status_helga_ok_nc_ot_np_cc(self):
        self.assertEqual(calcularPontosStatusHelga('H Adulto E', STATUS_OK, 1, regras=REGRAS), 40)
        self.assertEqual(calcularPontosStatusHelga('H Adulto E', STATUS_NC, None, regras=REGRAS), 1)
        self.assertEqual(calcularPontosStatusHelga('D Master B', STATUS_OT, None, regras=REGRAS), 1)
        self.assertEqual(calcularPontosStatusHelga('H Vet A', STATUS_NP, None, regras=REGRAS), 0)
        self.assertEqual(calcularPontosStatusHelga('H Vet B', STATUS_CC, None, regras=REGRAS), 0)

    def test_categorias_acompanhadas_e_abertas_nao_pontuam(self):
        for cat in ('HN1', 'DN2', 'Acompanhado Adulto', 'Aberto Curto'):
            self.assertTrue(ehCategoriaSemPontuacao(cat))
            self.assertEqual(calcularPontosEtapa(cat, True, 1, regras=REGRAS), 0)


class TestDescarteEVoluntarios(unittest.TestCase):
    def test_direito_descarte_cco_apenas_mais_de_3_etapas(self):
        self.assertFalse(temDireitoDescarteCCO(2, REGRAS))
        self.assertFalse(temDireitoDescarteCCO(3, REGRAS))
        self.assertTrue(temDireitoDescarteCCO(4, REGRAS))

    def test_penalidade_art23_impede_descarte_daquela_etapa(self):
        notas = [
            (Decimal('1'), False),   # Etapa 1: penalizado pelo Art. 23 (não pode descartar)
            (Decimal('35'), True),   # Etapa 2
            (Decimal('40'), True),   # Etapa 3
            (Decimal('37'), True),   # Etapa 4
        ]
        self.assertEqual(selecionarIndiceDescarte(notas), 1)

    def test_minimo_etapas_voluntario_arredonda_para_baixo(self):
        self.assertEqual(calcularMinimoMetadeEtapas(4, REGRAS), 2)
        self.assertEqual(calcularMinimoMetadeEtapas(5, REGRAS), 2)
        self.assertEqual(calcularMinimoMetadeEtapas(3, REGRAS), 1)

    def test_media_voluntario_cco_aplica_descarte_antes_da_media(self):
        media = calcularMediaVoluntarioCCO(
            etapasRealizadasNoCampeonato=4,
            resultadosInscritosExcetoVoluntario=[(40, True), (35, True), (10, True)],
            participouEtapasTotais=3,
            regras=REGRAS,
        )
        self.assertEqual(media, Decimal('37.50'))

    def test_leitura_voluntarios_markdown(self):
        md = (
            "## Voluntários por Etapa\n\n"
            "| Etapa | CBO | Voluntário / Convocado |\n"
            "| :---: | :---: | :--- |\n"
            "| 1ª | 10641 | Antonio Marden Oliveira de Sousa |\n"
            "| 2ª | 786 | Wladimir Sant'Anna |\n\n"
            "## Árbitros Convocados pela FECORI\n\n"
            "| Etapa | CBO | Árbitro | QA/FECORI |\n"
            "| :---: | :---: | :--- | :---: |\n"
            "| 1ª | 4316 | Jorge Saraiva de Amorim | 65 |\n\n"
            "## Unificação de Cadastros (CBO Provisório para CBO Oficial)\n\n"
            "| CBO Provisório | CBO Oficial | Atleta | Clube Oficial |\n"
            "| :---: | :---: | :--- | :---: |\n"
            "| 990004 | 24219 | Samilla Pontes Braga | TRILHA NORTE |\n"
        )
        lido = lerVoluntariosMarkdown(md)
        self.assertEqual(len(lido['voluntarios']), 3)
        self.assertEqual(len(lido['arbitros']), 1)
        self.assertEqual(len(lido['unificacoesCbo']), 1)
        self.assertEqual(lido['voluntarios'][0]['etapa'], 1)
        self.assertEqual(lido['voluntarios'][0]['cbo'], 10641)
        self.assertEqual(lido['voluntarios'][0]['funcao'], 'voluntario')
        self.assertEqual(lido['voluntarios'][1]['etapa'], 2)
        self.assertEqual(lido['voluntarios'][1]['cbo'], 786)
        self.assertEqual(lido['arbitros'][0]['etapa'], 1)
        self.assertEqual(lido['arbitros'][0]['cbo'], 4316)
        self.assertEqual(lido['arbitros'][0]['qaFecori'], 65)
        self.assertEqual(lido['arbitros'][0]['funcao'], 'arbitro')
        self.assertEqual(lido['unificacoesCbo'][0]['cboProvisorio'], 990004)
        self.assertEqual(lido['unificacoesCbo'][0]['cboOficial'], 24219)
        self.assertEqual(lido['unificacoesCbo'][0]['clubeSigla'], 'TRILHA NORTE')


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
        total = calcularPontuacaoClubeNaEtapa(pontosPorCategoria, clubeFiliadoCBO=True)
        self.assertEqual(total, Decimal('185.00'))

    def test_clube_nao_filiado_nao_pontua(self):
        pontosPorCategoria = {'H21E': [(Decimal('40'), True)]}
        self.assertEqual(
            calcularPontuacaoClubeNaEtapa(pontosPorCategoria, clubeFiliadoCBO=False),
            Decimal('0.00'),
        )

    def test_normalizacao_categoria_padrao_e_formatacao_relatorio(self):
        self.assertEqual(normalizarCategoriaPadraoCBO('D21B'), 'D Adulto B')
        self.assertEqual(normalizarCategoriaPadraoCBO('H65A'), 'H65A')
        self.assertEqual(formatarPontoTabelaParcial(Decimal('40.00')), '40')
        self.assertEqual(formatarPontoTabelaParcial(Decimal('36.50')), '36,5')
        self.assertEqual(sanitizarCelulaExcel('=SUM(A1:A2)'), "'=SUM(A1:A2)")


if __name__ == '__main__':
    unittest.main()
