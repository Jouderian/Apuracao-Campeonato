# -*- coding: utf-8 -*-
"""Testes da Camada B da análise de desempenho: parciais por posto e ritmo por trecho."""
import unittest
from typing import Any

from src.analises.parciais import calcularRitmosPorTrecho
from src.analises.ritmo import formatarRitmo
from src.extracaoAccess.extrairParciais import montarParciais
from src.extracaoAccess.validarEntrada import EntradaInvalidaError, validarDadosParciais

HASH = "a" * 64


def _concluinte(runnerPk: int, chip: int | None, tempo: str | None, percursoId: int | None = 10) -> dict[str, Any]:
    return {"competitionId": 36, "runnerPk": runnerPk, "percursoId": percursoId, "chip": chip, "tempo": tempo}


def _passagens(leituraId: int, trechos: list[tuple[int, int | None]]) -> list[dict[str, Any]]:
    return [
        {"leituraId": leituraId, "ordem": i, "codigoPosto": codigo, "tempoParcialSegundos": segundos}
        for i, (codigo, segundos) in enumerate(trechos, start=1)
    ]


def _bruto() -> dict[str, Any]:
    # Percurso 10: postos 31, 32 e chegada 999, com 400 m, 600 m e 100 m.
    return {
        "postos": [
            {"percursoId": 10, "ordem": 1, "codigoPosto": 31, "distanciaM": 400},
            {"percursoId": 10, "ordem": 2, "codigoPosto": 32, "distanciaM": 600},
            {"percursoId": 10, "ordem": 3, "codigoPosto": 999, "distanciaM": 0},
        ],
        "concluintes": [
            _concluinte(1, 111, "00:10:00"),    # duas leituras: vale a última
            _concluinte(2, 222, "00:12:00"),    # soma diverge do tempo oficial
            _concluinte(3, 333, "00:09:00"),    # posto 32 pulado: sequência difere
            _concluinte(4, None, "00:09:00"),   # sem chip
            _concluinte(5, 555, "00:09:00"),    # chip sem leitura no banco
            _concluinte(6, 666, "00:10:00", percursoId=None),
            _concluinte(7, 777, "00:10:01"),    # diferença de 1 s: aceita
        ],
        "leituras": [
            {"leituraId": 1, "competitionId": 36, "chip": 111},
            {"leituraId": 2, "competitionId": 36, "chip": 111},
            {"leituraId": 3, "competitionId": 36, "chip": 222},
            {"leituraId": 4, "competitionId": 36, "chip": 333},
            {"leituraId": 5, "competitionId": 36, "chip": 777},
        ],
        "passagens": (
            _passagens(1, [(31, 100)])                                   # leitura antiga, parcial: ignorada
            + _passagens(2, [(31, 240), (32, 300), (999, 60)])           # 600 s: fecha com 00:10:00
            + _passagens(3, [(31, 240), (32, 300), (999, 60)])           # 600 s contra 720 s oficiais
            + _passagens(4, [(31, 300), (999, 240)])                     # 540 s, sem o posto 32
            + _passagens(5, [(31, 240), (32, 300), (999, 60)])           # 600 s contra 601 s oficiais
        ),
    }


class TestMontarParciais(unittest.TestCase):
    def setUp(self):
        self.dados = montarParciais(_bruto(), "Sintetico.mdb", HASH)
        self.participacoes = {p["runnerPk"]: p for p in self.dados["participacoes"]}
        self.motivos = {o["runnerPk"]: o["motivo"] for o in self.dados["ocorrencias"]}

    def test_vale_a_ultima_leitura_do_chip(self):
        passagens = self.participacoes[1]["passagens"]
        self.assertEqual([p["tempoParcialSegundos"] for p in passagens], [240, 300, 60])
        self.assertTrue(self.participacoes[1]["postosConferem"])
        self.assertNotIn(1, self.motivos)

    def test_soma_que_nao_fecha_o_tempo_oficial_fica_sem_parciais_e_com_ocorrencia(self):
        self.assertNotIn(2, self.participacoes)
        self.assertEqual(self.motivos[2], "soma das parciais (600 s) diverge do tempo oficial (720 s)")

    def test_tolerancia_de_1_segundo_na_soma(self):
        self.assertIn(7, self.participacoes)
        self.assertEqual(self.participacoes[7]["tempoOficialSegundos"], 601)

    def test_sequencia_de_postos_diferente_mantem_parciais_marcadas(self):
        self.assertIn(3, self.participacoes)
        self.assertFalse(self.participacoes[3]["postosConferem"])
        self.assertEqual(self.motivos[3], "sequência de postos lida difere da do percurso")

    def test_motivos_de_quem_nao_tem_parciais(self):
        self.assertEqual(self.motivos[4], "sem chip registrado")
        self.assertEqual(self.motivos[5], "sem leitura do chip")
        self.assertEqual(self.motivos[6], "sem percurso")

    def test_distancia_zero_do_trecho_vira_nulo_e_chip_nao_vai_para_o_json(self):
        postos = self.dados["percursos"][0]["postos"]
        self.assertEqual([p["distanciaM"] for p in postos], [400, 600, None])
        texto = str(self.dados)
        for numeroDoChip in ("111", "222", "333", "555", "666", "777"):
            self.assertNotIn(numeroDoChip, texto)
        self.assertNotIn("'chip'", texto)

    def test_passagem_com_parcial_ausente_e_recusada(self):
        bruto = _bruto()
        bruto["passagens"] += _passagens(6, [(31, None)])
        bruto["leituras"].append({"leituraId": 6, "competitionId": 36, "chip": 111})
        dados = montarParciais(bruto, "Sintetico.mdb", HASH)
        motivos = {o["runnerPk"]: o["motivo"] for o in dados["ocorrencias"]}
        self.assertEqual(motivos[1], "parcial ausente na última leitura")


class TestValidarParciais(unittest.TestCase):
    def _valido(self) -> dict[str, Any]:
        return montarParciais(_bruto(), "Sintetico.mdb", HASH)

    def test_aceita_json_valido(self):
        validarDadosParciais(self._valido())

    def test_recusa_campo_de_dado_pessoal(self):
        dados = self._valido()
        dados["participacoes"][0]["anoNascimento"] = 1980
        with self.assertRaises(EntradaInvalidaError):
            validarDadosParciais(dados)

    def test_recusa_percurso_inexistente_e_hash_invalido(self):
        dados = self._valido()
        dados["participacoes"][0]["percursoId"] = 999
        with self.assertRaises(EntradaInvalidaError):
            validarDadosParciais(dados)
        dados = self._valido()
        dados["sha256Fonte"] = "xyz"
        with self.assertRaises(EntradaInvalidaError) as ctx:
            validarDadosParciais(dados)
        self.assertIn("sha256Fonte", str(ctx.exception))


class TestRitmoPorTrecho(unittest.TestCase):
    def test_ritmo_de_cada_trecho_com_a_distancia_do_trecho(self):
        dados = montarParciais(_bruto(), "Sintetico.mdb", HASH)
        ritmos, semRitmo = calcularRitmosPorTrecho(dados)
        doAtleta1 = {r.ordem: r for r in ritmos if r.runnerPk == 1}
        # 240 s em 400 m = 600 s/km (10'00"); 300 s em 600 m = 500 s/km (8'20").
        self.assertEqual(formatarRitmo(doAtleta1[1].ritmoSegundosPorKm), "10'00\"")
        self.assertEqual(formatarRitmo(doAtleta1[2].ritmoSegundosPorKm), "8'20\"")
        self.assertEqual(doAtleta1[1].distanciaM, 400)
        # Chegada sem distância no Helga: sem ritmo, com o motivo.
        self.assertNotIn(3, doAtleta1)
        motivos = {(s.runnerPk, s.ordem): s.motivo for s in semRitmo}
        self.assertEqual(motivos[(1, 3)], "trecho sem distância")

    def test_sequencia_divergente_fica_sem_ritmo_por_trecho(self):
        dados = montarParciais(_bruto(), "Sintetico.mdb", HASH)
        ritmos, semRitmo = calcularRitmosPorTrecho(dados)
        self.assertFalse([r for r in ritmos if r.runnerPk == 3])
        self.assertIn((3, None, "sequência de postos difere do percurso"),
                      [(s.runnerPk, s.ordem, s.motivo) for s in semRitmo])

    def test_parcial_zero_fica_sem_ritmo(self):
        dados = montarParciais(_bruto(), "Sintetico.mdb", HASH)
        dados["participacoes"][0]["passagens"][0]["tempoParcialSegundos"] = 0
        ritmos, semRitmo = calcularRitmosPorTrecho(dados)
        self.assertNotIn((1, 1), {(r.runnerPk, r.ordem) for r in ritmos})
        self.assertIn("parcial zero ou negativa", [s.motivo for s in semRitmo])


if __name__ == "__main__":
    unittest.main()
