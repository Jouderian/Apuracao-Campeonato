# -*- coding: utf-8 -*-
"""Testes do regulamento por ano: cada edição é apurada pelo regulamento do seu próprio ano (ADR-005).

Cobre o registro de regras (ano sem regras é recusado), as diferenças entre 2025 (Arts. 34 a 42, sem
descarte) e 2026 (Arts. 31 a 39) e os relatórios com etapas ausentes (2025 não tem a 2ª etapa no Helga).
"""
from contextlib import redirect_stderr
from decimal import Decimal
import io
import os
import tempfile
import unittest
from unittest import mock

from src import apurarCampeonato
from src.motorCalculo.pontuacao import (
    STATUS_NC,
    apurarCampeonatoCCO,
    calcularMediaVoluntarioCCO,
    calcularPontosEtapa,
    diagnosticarEtapas,
    temDireitoDescarteCCO,
)
from src.motorCalculo.regulamentos import (
    REGRAS_CCO_2024,
    REGRAS_CCO_2025,
    REGRAS_CCO_2026,
    RegulamentoNaoMapeadoError,
    anosMapeados,
    calcularMinimoMetadeEtapas,
    obterRegras,
)
from src.relatorios.geradorExcelPdf import gerarPdfResultadoParcialAtletas, gerarPlanilhaExcelApuracao
from src.relatorios.geradorMarkdown import (
    gerarRelatorioClubesMarkdown,
    gerarRelatorioIndividualMarkdown,
)
from tests.test_apuracao_integracao import CATEGORIA, _registro, montarDadosSinteticos


def _dados(etapas: tuple[int, ...], registros: list[dict], voluntarios: list[dict] | None = None):
    dadosHelga = {
        "fonte": "Sintetico.mdb",
        "sha256Fonte": "0" * 64,
        "etapas": [{"numeroEtapa": n, "descricao": f"{n}ª etapa", "data": "2025-01-01", "local": "L",
                    "clubeOrganizadorSigla": "AAA"} for n in etapas],
        "clubes": [{"clubeId": 1, "sigla": "AAA", "nome": "Clube A", "filiadoCBO": True, "federacaoSigla": "FECORI"}],
        "perfisAtletas": {},
        "registrosEtapas": registros,
    }
    return dadosHelga, {"voluntarios": voluntarios or [], "penalidadesArt23": []}


def _fichas(resultado) -> dict:
    return {f.cbo: f for f in resultado["fichasPorCategoria"][CATEGORIA]}


class TestRegistroDeRegras(unittest.TestCase):
    def test_2024_2025_e_2026_estao_registrados_com_seus_artigos(self):
        self.assertIs(obterRegras(2024), REGRAS_CCO_2024)
        self.assertIs(obterRegras(2025), REGRAS_CCO_2025)
        self.assertIs(obterRegras(2026, "cco"), REGRAS_CCO_2026)
        self.assertEqual(anosMapeados(), [2024, 2025, 2026])
        self.assertEqual(REGRAS_CCO_2024.artigos.voluntarios, "Art. 36")
        self.assertEqual(REGRAS_CCO_2025.artigos.voluntarios, "Art. 36")
        self.assertEqual(REGRAS_CCO_2026.artigos.voluntarios, "Art. 33")

    def test_ano_sem_regras_e_recusado_sem_usar_ano_vizinho(self):
        for ano in (2023, 2027):
            with self.assertRaises(RegulamentoNaoMapeadoError) as ctx:
                obterRegras(ano)
            self.assertIn(str(ano), str(ctx.exception))
            self.assertIn("Regulamentos-de-Orientacao", str(ctx.exception))

    def test_competicao_sem_regras_e_recusada(self):
        with self.assertRaises(RegulamentoNaoMapeadoError):
            obterRegras(2026, "CCOS")

    def test_cli_recusa_ano_sem_regras_antes_de_ler_dados(self):
        erro = io.StringIO()
        with mock.patch("sys.argv", ["apurarCampeonato.py", "--ano", "2023"]), redirect_stderr(erro):
            self.assertEqual(apurarCampeonato.main(), 1)
        self.assertIn("Regulamento não mapeado", erro.getvalue())

    def test_cli_exige_o_ano_sem_valor_padrao(self):
        with mock.patch("sys.argv", ["apurarCampeonato.py"]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                apurarCampeonato.main()


class TestRegrasDeCadaAno(unittest.TestCase):
    def test_2024_e_2025_nunca_tem_descarte_e_2026_so_com_mais_de_3_etapas(self):
        for etapas in (1, 3, 4, 8):
            self.assertFalse(temDireitoDescarteCCO(etapas, REGRAS_CCO_2024))
            self.assertFalse(temDireitoDescarteCCO(etapas, REGRAS_CCO_2025))
        self.assertFalse(temDireitoDescarteCCO(3, REGRAS_CCO_2026))
        self.assertTrue(temDireitoDescarteCCO(4, REGRAS_CCO_2026))

    def test_minimo_de_metade_arredonda_para_baixo_em_2026_e_para_cima_em_2024_e_2025(self):
        self.assertEqual([calcularMinimoMetadeEtapas(n, REGRAS_CCO_2026) for n in (3, 4, 5)], [1, 2, 2])
        self.assertEqual([calcularMinimoMetadeEtapas(n, REGRAS_CCO_2024) for n in (3, 4, 5)], [2, 2, 3])
        self.assertEqual([calcularMinimoMetadeEtapas(n, REGRAS_CCO_2025) for n in (3, 4, 5)], [2, 2, 3])

    def test_tabela_de_pontos_de_2025(self):
        pontos = [calcularPontosEtapa("H21E", True, c, regras=REGRAS_CCO_2025) for c in (1, 2, 26, 27, 40)]
        self.assertEqual(pontos, [40, 37, 11, 10, 10])
        self.assertEqual(calcularPontosEtapa("H21E", False, None, regras=REGRAS_CCO_2025), 1)

    def test_media_de_voluntario_so_aplica_descarte_quando_o_ano_prevê(self):
        notas = [(40, True), (35, True), (10, True)]
        com = calcularMediaVoluntarioCCO(4, notas, 3, regras=REGRAS_CCO_2026)   # descarta o 10: (40+35)/2
        sem = calcularMediaVoluntarioCCO(4, notas, 3, regras=REGRAS_CCO_2025)   # sem descarte: 85/3
        self.assertEqual(com, Decimal("37.50"))
        self.assertEqual(sem.quantize(Decimal("0.01")), Decimal("28.33"))   # 2025: fração exata, sem arredondar a média


class TestApuracao2025(unittest.TestCase):
    def test_sem_descarte_soma_todas_as_etapas_e_voluntario_recebe_media_sem_descarte(self):
        dadosHelga, dadosVoluntarios = montarDadosSinteticos()
        resultado = apurarCampeonatoCCO(dadosHelga, dadosVoluntarios, REGRAS_CCO_2025)
        fichas = _fichas(resultado)

        self.assertFalse(resultado["descarteAplicado"])
        self.assertTrue(all(f.etapaDescartada is None for f in fichas.values()))
        self.assertFalse(any(d.descartada for f in fichas.values() for d in f.etapas.values()))
        self.assertEqual(fichas[1].pontuacaoTotal, Decimal("160.00"))   # 4 x 40, nada descartado
        self.assertEqual(fichas[2].pontuacaoTotal, Decimal("111.00"))   # 37 x 3 + 0 na 4ª etapa
        # Caio: demais etapas 35, 35 e 37, sem descarte: média 35,67 (em 2026 seria 36,00 após o descarte)
        self.assertEqual(fichas[3].etapas[2].pontosFinais.quantize(Decimal("0.01")), Decimal("35.67"))
        self.assertEqual(fichas[3].pontuacaoTotal, Decimal("142.67"))   # 35 + 35,67 + 35 + 37

    def test_mesmos_dados_apurados_por_2026_mantem_o_descarte(self):
        resultado = apurarCampeonatoCCO(*montarDadosSinteticos(), REGRAS_CCO_2026)
        self.assertTrue(resultado["descarteAplicado"])
        self.assertEqual(_fichas(resultado)[1].pontuacaoTotal, Decimal("120.00"))

    def test_2025_exige_competir_e_2026_conta_a_etapa_de_apoio_no_minimo_do_voluntario(self):
        registros = [_registro(e, 1, "Ana", 1000) for e in (1, 2, 3)]
        registros.append(_registro(1, 4, "Dani", 1100))       # Dani compete só na 1ª etapa (2ª colocada, 37)
        dadosHelga, dadosVol = _dados((1, 2, 3), registros, [{"etapa": 2, "cbo": 4, "nome": "Dani"}])

        r2025 = _fichas(apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025))[4]
        r2026 = _fichas(apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2026))[4]
        # 2025 (Art. 36, § 1º): o voluntário deve competir em 2 das 3 etapas e Dani competiu em 1: sem média.
        self.assertEqual(r2025.etapas[2].pontosFinais, Decimal("0.00"))
        self.assertEqual(r2025.pontuacaoTotal, Decimal("37.00"))
        # 2026 (Art. 33, § 1º, "participar"): a etapa de apoio conta (1 + 1 de 3, mínimo 1) e a média é só sobre as
        # etapas em que se inscreveu (a 1ª): 37.
        self.assertEqual(r2026.etapas[2].pontosFinais, Decimal("37.00"))
        self.assertEqual(r2026.pontuacaoTotal, Decimal("74.00"))

    def test_2025_voluntario_precisa_competir_em_metade_das_etapas_sem_contar_a_de_apoio(self):
        registros = [_registro(e, 1, "Ana", 1000) for e in (1, 2, 3, 4)]
        registros.append(_registro(3, 4, "Dani", 1100))       # Dani compete só na 3ª etapa (2º colocado, 37 pontos)
        dadosHelga, dadosVol = _dados((1, 2, 3, 4), registros, [{"etapa": 2, "cbo": 4, "nome": "Dani"}])
        ficha = _fichas(apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025))[4]
        # Competiu em 1 de 4 etapas (mínimo 2): a etapa de apoio não conta, então não há média.
        self.assertEqual(ficha.etapas[2].pontosFinais, Decimal("0.00"))
        # Competindo também na 1ª etapa, são 2 de 4: média = (37 + 37) / 3 outras etapas = 24,67.
        registros.append(_registro(1, 4, "Dani", 1100))
        ficha2 = _fichas(apurarCampeonatoCCO(*_dados((1, 2, 3, 4), registros, [{"etapa": 2, "cbo": 4, "nome": "Dani"}]),
                                              REGRAS_CCO_2025))[4]
        self.assertEqual(ficha2.etapas[2].pontosFinais.quantize(Decimal("0.01")), Decimal("24.67"))

    def test_outra_etapa_de_apoio_entra_com_zero_no_divisor(self):
        registros = [_registro(e, 1, "Ana", 1000) for e in (1, 2, 3, 4)]
        registros += [_registro(1, 4, "Dani", 1100), _registro(3, 4, "Dani", 1100)]   # 2º nas etapas 1 e 3: 37 + 37
        vol = [{"etapa": 2, "cbo": 4, "nome": "Dani"}, {"etapa": 4, "cbo": 4, "nome": "Dani"}]
        ficha = _fichas(apurarCampeonatoCCO(*_dados((1, 2, 3, 4), registros, vol), REGRAS_CCO_2025))[4]
        # Média de cada etapa de apoio: (37 + 37 + 0 da outra etapa de apoio) / 3 = 24,67.
        self.assertEqual(ficha.etapas[2].pontosFinais.quantize(Decimal("0.01")), Decimal("24.67"))
        self.assertEqual(ficha.etapas[4].pontosFinais.quantize(Decimal("0.01")), Decimal("24.67"))
        # 37 + 24,67 + 37 + 24,67 (cada média arredondada a 2 casas, como em 2026), sem descarte
        self.assertEqual(ficha.pontuacaoTotal, Decimal("123.34"))

    def test_voluntario_de_etapa_ausente_dos_dados_nao_cria_ficha(self):
        registros = [_registro(e, 1, "Ana", 1000) for e in (1, 3, 4)]
        dadosHelga, dadosVol = _dados((1, 3, 4), registros, [{"etapa": 2, "cbo": 99, "nome": "Fantasma"}])
        resultado = apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        self.assertNotIn(99, _fichas(resultado))
        self.assertEqual(resultado["etapasComVoluntarios"], [2])   # a lista informada continua, sem efeito no cálculo


class TestDesempate2025(unittest.TestCase):
    def _empate_por_primeiros_lugares(self):
        """X (CBO 10): 1º na etapa 1 e 7º na 2; Y (CBO 11): 2º na 1 e 4º na 2. Ambos somam 70."""
        registros = [_registro(1, 10, "X", 1000), _registro(1, 11, "Y", 1100), _registro(2, 11, "Y", 1000),
                     _registro(2, 10, "X", 1100)]
        # Etapa 2: três atletas à frente de Y e dois entre Y e X, para X ser o 7º e Y o 4º.
        tempos = [(20, 900), (21, 901), (22, 902)]
        registros += [_registro(2, cbo, f"F{cbo}", t) for cbo, t in tempos]
        registros += [_registro(2, 23, "F23", 1050), _registro(2, 24, "F24", 1051)]
        registros[0]["tempoSegundos"] = 900   # X é o 1º na etapa 1 e Y o 2º
        registros[1]["tempoSegundos"] = 950
        return _dados((1, 2), registros)

    def test_mais_primeiros_lugares_desempata_em_2025(self):
        resultado = apurarCampeonatoCCO(*self._empate_por_primeiros_lugares(), REGRAS_CCO_2025)
        fichas = _fichas(resultado)
        self.assertEqual(fichas[10].pontuacaoTotal, fichas[11].pontuacaoTotal)
        self.assertEqual(fichas[10].pontuacaoTotal, Decimal("70.00"))
        self.assertLess(fichas[10].colocacaoNaCategoria, fichas[11].colocacaoNaCategoria)   # X tem um 1º lugar
        self.assertFalse(fichas[10].empateNaoResolvido or fichas[11].empateNaoResolvido)

    def test_mesmos_dados_em_2026_desempatam_pelo_ultimo_percurso(self):
        resultado = apurarCampeonatoCCO(*self._empate_por_primeiros_lugares(), REGRAS_CCO_2026)
        fichas = _fichas(resultado)
        # Na última etapa Y (4º, 33 pontos) supera X (7º, 30 pontos).
        self.assertLess(fichas[11].colocacaoNaCategoria, fichas[10].colocacaoNaCategoria)

    def test_ultimo_confronto_direto_resolve_quando_a_contagem_de_lugares_empata(self):
        registros = [
            _registro(1, 9, "R", 900), _registro(1, 11, "P", 1000), _registro(1, 12, "Q", 1100),
            _registro(2, 9, "R", 900), _registro(2, 12, "Q", 1000), _registro(2, 11, "P", 1100),
        ]
        resultado = apurarCampeonatoCCO(*_dados((1, 2), registros), REGRAS_CCO_2025)
        fichas = _fichas(resultado)
        self.assertEqual(fichas[11].pontuacaoTotal, fichas[12].pontuacaoTotal)   # 37 + 35 para ambos
        # Mesmo número de 2ºs e 3ºs lugares; na última etapa Q (2º) ficou à frente de P (3º), apesar do CBO maior.
        self.assertEqual([f.cbo for f in resultado["fichasPorCategoria"][CATEGORIA]], [9, 12, 11])
        self.assertFalse(any(f.empateNaoResolvido for f in fichas.values()))

    def test_sem_confronto_direto_o_empate_fica_sinalizado(self):
        registros = [_registro(1, 11, "P", 1000), _registro(2, 12, "Q", 1000)]
        resultado = apurarCampeonatoCCO(*_dados((1, 2), registros), REGRAS_CCO_2025)
        fichas = _fichas(resultado)
        self.assertTrue(fichas[11].empateNaoResolvido and fichas[12].empateNaoResolvido)
        markdown = gerarRelatorioIndividualMarkdown(2025, "XIX CCO", resultado)
        self.assertIn("Empate não resolvido (Art. 38, Parágrafo Único)", markdown)

    def test_nao_classificados_nao_formam_confronto_direto(self):
        def naoClassificado(etapa: int, cbo: int, nome: str) -> dict:
            reg = _registro(etapa, cbo, nome, 0)
            reg.update({"statusCodigo": STATUS_NC, "statusSigla": "NC", "tempo": None, "tempoSegundos": None})
            return reg

        # P: NC na etapa 1 (1 ponto) e 1º na 2 (40). Q: 1º na etapa 1 (40) e NC na 2 (1 ponto). Ambos somam 41.
        registros = [
            naoClassificado(1, 11, "P"), _registro(2, 11, "P", 1000),
            _registro(1, 12, "Q", 1000), naoClassificado(2, 12, "Q"),
        ]
        fichas = _fichas(apurarCampeonatoCCO(*_dados((1, 2), registros), REGRAS_CCO_2025))
        self.assertEqual(fichas[11].pontuacaoTotal, Decimal("41.00"))
        self.assertEqual(fichas[12].pontuacaoTotal, Decimal("41.00"))
        # Nunca foram classificados juntos na mesma etapa: não há confronto direto, o empate fica sinalizado.
        self.assertTrue(fichas[11].empateNaoResolvido and fichas[12].empateNaoResolvido)


class TestDiagnosticoDeEtapas(unittest.TestCase):
    def test_etapa_ausente_do_banco_e_etapa_sem_resultado_geram_aviso(self):
        reg3 = _registro(3, 1, "Ana", 0)
        reg3.update({"statusCodigo": 3, "statusSigla": "NP", "tempo": None, "tempoSegundos": None})
        dadosHelga, _ = _dados((1, 3, 4), [_registro(1, 1, "Ana", 1000), reg3, _registro(4, 1, "Ana", 1000)])
        avisos = diagnosticarEtapas(dadosHelga)
        self.assertEqual(len(avisos), 2)
        self.assertIn("2ª ausente(s) do banco", avisos[0])
        self.assertIn("3ª etapa sem nenhum resultado", avisos[1])

    def test_campeonato_completo_nao_gera_aviso(self):
        self.assertEqual(diagnosticarEtapas(montarDadosSinteticos()[0]), [])


class TestRelatorios2025(unittest.TestCase):
    """O Helga de 2025 só traz as etapas 1, 3 e 4; os relatórios mostram só essas e citam os artigos de 2025."""

    @classmethod
    def setUpClass(cls):
        registros = []
        for etapa in (1, 3, 4):
            registros.append(_registro(etapa, 1, "Ana", 1000))
            registros.append(_registro(etapa, 2, "Beto", 1100))
        voluntarios = [{"etapa": 3, "cbo": 2, "nome": "Beto"}]
        cls.resultado = apurarCampeonatoCCO(*_dados((1, 3, 4), registros, voluntarios), REGRAS_CCO_2025)
        cls.pasta = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.pasta.cleanup)

    def test_markdown_individual_cita_artigos_de_2025_e_so_as_etapas_realizadas(self):
        md = gerarRelatorioIndividualMarkdown(2025, "XIX CCO", self.resultado)
        self.assertIn("Regulamento do XIX Campeonato Cearense de Orientação (2025)", md)
        self.assertIn("Sem descarte (Art. 38)", md)
        self.assertIn("Voluntários e Árbitros (Art. 36, § 1º)", md)
        self.assertIn("| 1ª Etapa | 3ª Etapa | 4ª Etapa |", md)
        self.assertNotIn("2ª Etapa", md)
        self.assertNotIn("Art. 34, § 2º", md)
        self.assertNotIn("~~", md)   # nenhuma etapa tachada: não há descarte

    def test_markdown_de_clubes_cita_artigo_de_2025_e_so_as_etapas_realizadas(self):
        md = gerarRelatorioClubesMarkdown(2025, "XIX CCO", self.resultado)
        self.assertIn("**Art. 37**", md)
        self.assertIn("| 1ª Etapa | 3ª Etapa | 4ª Etapa | Total Pontos |", md)
        self.assertNotIn("2ª Etapa", md)

    def test_planilha_e_pdf_sao_gerados_com_tres_etapas_e_sem_coluna_de_descarte(self):
        from openpyxl import load_workbook
        import pymupdf as fitz

        caminhoXlsx = os.path.join(self.pasta.name, "apuracao2025.xlsx")
        gerarPlanilhaExcelApuracao(2025, "XIX CCO", "XIX", self.resultado, caminhoXlsx)
        wb = load_workbook(caminhoXlsx)
        cabecalhoIndiv = [c.value for c in wb["resultadoIndividual"][3]]
        self.assertNotIn("Etapa Descartada", cabecalhoIndiv)
        self.assertIn("E3 Pts", cabecalhoIndiv)
        self.assertNotIn("E2 Pts", cabecalhoIndiv)
        self.assertIn("Elegível Premiação (Art. 42, § 1º)", cabecalhoIndiv)
        self.assertEqual([c.value for c in wb["resultadoParcial"][3]][5:9], ["1", "3", "4", "Total"])
        self.assertEqual(
            [c.value for c in wb["resultadoClubes"][3]][5:9], ["1ª Etapa", "3ª Etapa", "4ª Etapa", "Total Pontos"]
        )

        caminhoPdf = os.path.join(self.pasta.name, "parcial2025.pdf")
        gerarPdfResultadoParcialAtletas(2025, "XIX", self.resultado, [caminhoPdf], caminhoLogo=None)
        doc = fitz.open(caminhoPdf)
        self.addCleanup(doc.close)
        texto = doc[-1].get_text("text").replace("\xa0", " ").replace("\n", " ")
        self.assertIn("conforme estabelecido no Art. 36 do Regulamento", texto)
        self.assertNotIn("descarte da pontuação mais baixa", texto)


if __name__ == "__main__":
    unittest.main()
