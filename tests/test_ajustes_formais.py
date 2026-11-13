# -*- coding: utf-8 -*-
"""Mecanismos de ajuste por decisão formal da FECORI (ADR-008): notas, posições e omissões; hoje sem uso nos dados."""
from decimal import Decimal
import unittest

from src.extracaoAccess.leitorVoluntarios import lerVoluntariosMarkdown
from src.motorCalculo.pontuacao import apurarCampeonatoCCO
from src.motorCalculo.regulamentos import REGRAS_CCO_2025, REGRAS_CCO_2026
from src.relatorios.geradorMarkdown import gerarRelatorioIndividualMarkdown
from tests.test_apuracao_integracao import CATEGORIA, _registro, montarDadosSinteticos
from tests.test_regulamentos_por_ano import _dados, _fichas


class TestAjustesDeNotas(unittest.TestCase):
    def test_ajuste_substitui_a_nota_depois_do_calculo_e_e_sinalizado(self):
        dadosHelga, dadosVol = montarDadosSinteticos()
        dadosVol["ajustesOficiais"] = [
            {"etapa": 4, "cbo": 2, "categoria": CATEGORIA, "pontos": "10", "motivo": "publicado"},    # Beto, ausente na 4ª
            {"etapa": 1, "cbo": 3, "categoria": CATEGORIA, "pontos": "17,5", "motivo": "publicado"},  # vírgula decimal
        ]
        resultado = apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        fichas = _fichas(resultado)
        self.assertEqual(fichas[2].etapas[4].pontosFinais, Decimal("10.00"))
        self.assertTrue(fichas[2].etapas[4].ajustadoOficial)
        self.assertEqual(fichas[2].pontuacaoTotal, Decimal("121.00"))   # 37 x 3 + 10 do ajuste
        self.assertEqual(fichas[3].etapas[1].pontosFinais, Decimal("17.50"))
        self.assertEqual(len(resultado["ajustesOficiais"]), 2)
        md = gerarRelatorioIndividualMarkdown(2025, "XIX CCO", resultado)
        self.assertIn("10,00 (-)†", md)
        self.assertIn("2 notas (marcadas com †)", md)

    def test_ajuste_vale_depois_da_media_do_voluntario(self):
        dadosHelga, dadosVol = montarDadosSinteticos()   # Caio é voluntário na 2ª etapa
        dadosVol["ajustesOficiais"] = [{"etapa": 2, "cbo": 3, "categoria": CATEGORIA, "pontos": "0"}]
        ficha = _fichas(apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025))[3]
        self.assertEqual(ficha.etapas[2].pontosFinais, Decimal("0"))
        self.assertTrue(ficha.etapas[2].atuouComoVoluntario and ficha.etapas[2].ajustadoOficial)

    def test_ajustes_invalidos_recusam_a_apuracao(self):
        casos = {
            "sem ficha correspondente": {"etapa": 1, "cbo": 999, "categoria": CATEGORIA, "pontos": "10"},
            "pontos inválidos": {"etapa": 1, "cbo": 1, "categoria": CATEGORIA, "pontos": "dez"},
            "fora de 0 a 40": {"etapa": 1, "cbo": 1, "categoria": CATEGORIA, "pontos": "41"},
            "etapa ausente": {"etapa": 9, "cbo": 1, "categoria": CATEGORIA, "pontos": "10"},
        }
        for nome, ajuste in casos.items():
            dadosHelga, dadosVol = montarDadosSinteticos()
            dadosVol["ajustesOficiais"] = [ajuste]
            with self.subTest(nome), self.assertRaises(ValueError):
                apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        dadosHelga, dadosVol = montarDadosSinteticos()
        dadosVol["ajustesOficiais"] = [{"etapa": 1, "cbo": 1, "categoria": CATEGORIA, "pontos": "10"}] * 2
        with self.assertRaises(ValueError):   # repetido
            apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)


class TestPosicoesPublicadas(unittest.TestCase):
    def test_posicao_publicada_resolve_o_empate_e_limpa_o_aviso(self):
        registros = [_registro(1, 11, "P", 1000), _registro(2, 12, "Q", 1000)]   # empate sem confronto direto
        dadosHelga, dadosVol = _dados((1, 2), registros)
        antes = _fichas(apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025))
        self.assertTrue(antes[11].empateNaoResolvido)
        self.assertLess(antes[11].colocacaoNaCategoria, antes[12].colocacaoNaCategoria)
        dadosVol["posicoesOficiais"] = [
            {"categoria": CATEGORIA, "cbo": 12, "posicao": 1}, {"categoria": CATEGORIA, "cbo": 11, "posicao": 2},
        ]
        resultado = apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        fichas = _fichas(resultado)
        self.assertEqual([f.cbo for f in resultado["fichasPorCategoria"][CATEGORIA]], [12, 11])
        self.assertEqual((fichas[12].colocacaoFinal, fichas[11].colocacaoFinal), (1, 2))
        self.assertFalse(fichas[11].empateNaoResolvido or fichas[12].empateNaoResolvido)

    def test_posicoes_invalidas_recusam_a_apuracao(self):
        registros = [_registro(1, 11, "P", 1000), _registro(2, 12, "Q", 1000)]
        casos = {
            "sem ficha": [{"categoria": CATEGORIA, "cbo": 99, "posicao": 1}],
            "além do tamanho da categoria": [{"categoria": CATEGORIA, "cbo": 11, "posicao": 5}],
            "posições repetidas": [
                {"categoria": CATEGORIA, "cbo": 11, "posicao": 1}, {"categoria": CATEGORIA, "cbo": 12, "posicao": 1},
            ],
        }
        for nome, posicoes in casos.items():
            dadosHelga, dadosVol = _dados((1, 2), registros)
            dadosVol["posicoesOficiais"] = posicoes
            with self.subTest(nome), self.assertRaises(ValueError):
                apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)


class TestClubes2025(unittest.TestCase):
    def _quatro_atletas_duas_etapas(self):
        # Etapa 1: D, A, B, C; etapa 2: A, B, C, D. Totais: A 77, D 73, B 72, C 68.
        tempos = {1: {4: 900, 1: 1000, 2: 1100, 3: 1200}, 2: {1: 900, 2: 1000, 3: 1100, 4: 1200}}
        nomes = {1: "A", 2: "B", 3: "C", 4: "D"}
        return _dados((1, 2), [_registro(e, c, nomes[c], t) for e, ts in tempos.items() for c, t in ts.items()])

    def test_2025_e_2026_somam_os_3_melhores_de_cada_categoria_por_etapa(self):
        for regras in (REGRAS_CCO_2025, REGRAS_CCO_2026):
            with self.subTest(ano=regras.ano):
                resultado = apurarCampeonatoCCO(*self._quatro_atletas_duas_etapas(), regras)
                clube = resultado["classificacaoClubes"][0]
                self.assertEqual(clube["totalPontos"], Decimal("224.00"))   # 112 + 112 por etapa
                # Etapa 1: A 37... os 3 melhores da etapa; a quarta colocada fica de fora em cada etapa.
                self.assertEqual(len(clube["detalheTop3PorEtapa"][1][CATEGORIA]), 3)
                self.assertEqual(sum(clube["pontosPorEtapa"].values()), Decimal("224.00"))


def _naoLargou(etapa: int, cbo: int, nome: str) -> dict:
    reg = _registro(etapa, cbo, nome, 0)
    reg.update({"statusCodigo": 3, "statusSigla": "NP", "tempo": None, "tempoSegundos": None})
    return reg


class TestRegrasDeClubes(unittest.TestCase):
    def test_clube_de_outra_federacao_nao_e_classificado_em_2025_mas_e_em_2026(self):
        reg = _registro(1, 8, "Ze", 1100)
        reg.update({"clubeId": 2, "clubeSigla": "BBB", "clubeNome": "Clube B"})
        dadosHelga, dadosVol = _dados((1,), [_registro(1, 1, "Ana", 1000), reg])
        dadosHelga["clubes"].append(
            {"clubeId": 2, "sigla": "BBB", "nome": "Clube B", "filiadoCBO": True, "federacaoSigla": "FOMS"})
        siglas2025 = [c["sigla"] for c in apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)["classificacaoClubes"]]
        siglas2026 = [c["sigla"] for c in apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2026)["classificacaoClubes"]]
        self.assertEqual(siglas2025, ["AAA"])
        self.assertEqual(sorted(siglas2026), ["AAA", "BBB"])

    def test_coluna_atletas_conta_atletas_distintos_nos_dois_anos(self):
        outraCategoria = _registro(2, 5, "Eva", 1000)
        outraCategoria["categoria"] = "H Adulto B"
        registros = [_registro(1, 1, "Ana", 1000), _registro(1, 5, "Eva", 1100), outraCategoria]
        dados = _dados((1, 2), registros)
        for regras in (REGRAS_CCO_2025, REGRAS_CCO_2026):
            with self.subTest(ano=regras.ano):
                self.assertEqual(apurarCampeonatoCCO(*dados, regras)["classificacaoClubes"][0]["qtdAtletas"], 2)


class TestOmissoesDoPublicado(unittest.TestCase):
    def _dados(self):
        return _dados((1,), [_registro(1, 1, "Ana", 1000), _naoLargou(1, 4, "Dani")])

    def test_atleta_omitido_sai_do_resultado(self):
        dadosHelga, dadosVol = self._dados()
        com = apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        self.assertIn(4, _fichas(com))
        dadosVol["omissoesOficiais"] = [{"categoria": CATEGORIA, "cbo": 4, "motivo": "fora da lista publicada"}]
        sem = apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)
        self.assertNotIn(4, _fichas(sem))
        self.assertEqual(sem["omissoesOficiais"], [{"categoria": CATEGORIA, "cbo": 4}])
        self.assertIn("1 atletas fora da lista", gerarRelatorioIndividualMarkdown(2025, "XIX CCO", sem))

    def test_omissoes_invalidas_recusam_a_apuracao(self):
        casos = {
            "atleta com pontos": {"categoria": CATEGORIA, "cbo": 1},
            "sem ficha correspondente": {"categoria": CATEGORIA, "cbo": 99},
        }
        for nome, omissao in casos.items():
            dadosHelga, dadosVol = self._dados()
            dadosVol["omissoesOficiais"] = [omissao]
            with self.subTest(nome), self.assertRaises(ValueError):
                apurarCampeonatoCCO(dadosHelga, dadosVol, REGRAS_CCO_2025)

    def test_leitura_da_secao_de_atletas_fora_do_resultado(self):
        md = (
            "## Atletas Fora do Resultado Oficial Publicado\n\n"
            "| Categoria | CBO | Motivo |\n| :--- | :---: | :--- |\n"
            "| H Vet A | 10641 | Voluntário sem inscrição nas etapas apuradas |\n"
        )
        self.assertEqual(lerVoluntariosMarkdown(md)["omissoesOficiais"], [
            {"categoria": "H Vet A", "cbo": 10641, "motivo": "Voluntário sem inscrição nas etapas apuradas"}])


class TestLeituraDasSecoes(unittest.TestCase):
    def test_leitura_das_secoes_de_ajustes_e_posicoes(self):
        md = (
            "## Ajustes do Resultado Oficial Publicado\n\n"
            "| Etapa | CBO | Categoria | Pontos publicados | Motivo | Destaque |\n"
            "| :---: | :---: | :--- | :---: | :--- | :---: |\n"
            "| 3ª | 16453 | H Vet A | 21 | Publicado 21 | |\n"
            "| 1ª | 3952 | H Vet A | 17,5 | Média lançada | Média |\n\n"
            "## Desempates Decididos pela FECORI\n\n"
            "| Categoria | CBO | Posição publicada | Motivo |\n| :--- | :---: | :---: | :--- |\n"
            "| D Juven B | 22516 | 2 | Empate resolvido no publicado |\n"
        )
        lido = lerVoluntariosMarkdown(md)
        self.assertEqual(lido["ajustesOficiais"], [
            {"etapa": 3, "cbo": 16453, "categoria": "H Vet A", "pontos": "21", "motivo": "Publicado 21", "destaque": ""},
            {"etapa": 1, "cbo": 3952, "categoria": "H Vet A", "pontos": "17,5", "motivo": "Média lançada",
             "destaque": "média"},
        ])
        self.assertEqual(lido["posicoesOficiais"], [
            {"categoria": "D Juven B", "cbo": 22516, "posicao": 2, "motivo": "Empate resolvido no publicado"}])
        self.assertEqual(lido["voluntarios"], [])


if __name__ == "__main__":
    unittest.main()
