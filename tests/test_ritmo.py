# -*- coding: utf-8 -*-
"""Testes da Camada A da análise de desempenho: percursos, validação e ritmo médio."""
import copy
import unittest
from typing import Any

from src.analises.ritmo import calcularRitmos, calcularRitmoSegundosPorKm, formatarRitmo
from src.extracaoAccess.extrairPercursos import montarPercursos
from src.extracaoAccess.validarEntrada import EntradaInvalidaError, validarDadosPercursos

HASH = "a" * 64


def _bruto() -> dict[str, Any]:
    return {
        "percursos": [
            {"percursoId": 20, "competitionId": 36, "numero": 2, "nome": "", "distanciaM": 1500, "subidaM": 0},
            {"percursoId": 10, "competitionId": 36, "numero": 1, "nome": "", "distanciaM": 4000, "subidaM": 110},
            {"percursoId": 30, "competitionId": 36, "numero": 3, "nome": "", "distanciaM": 0, "subidaM": None},
        ],
        "categoriaPercurso": [
            {"competitionId": 36, "categoriaId": 2, "categoria": "D Adulto N", "percursoId": 20},
            {"competitionId": 36, "categoriaId": 1, "categoria": "H Adulto E", "percursoId": 10},
        ],
        "participacoes": [
            {"competitionId": 36, "runnerPk": 2, "percursoId": 20, "statusCodigo": 0,
             "horaLargada": "09:00:00", "horaChegada": "09:23:01"},
            {"competitionId": 36, "runnerPk": 1, "percursoId": 10, "statusCodigo": 0,
             "horaLargada": "09:00:00", "horaChegada": "10:03:26"},
            {"competitionId": 36, "runnerPk": 3, "percursoId": 30, "statusCodigo": 3,
             "horaLargada": None, "horaChegada": None},
            {"competitionId": 36, "runnerPk": 4, "percursoId": None, "statusCodigo": 3,
             "horaLargada": None, "horaChegada": None},
        ],
    }


def _dadosEtapas() -> dict[str, Any]:
    def reg(runnerPk: int, cbo: int, nome: str, categoria: str, status: int, sigla: str,
            tempo: int | None) -> dict[str, Any]:
        return {"etapa": 2, "competitionId": 36, "runnerPk": runnerPk, "cbo": cbo, "nome": nome,
                "categoria": categoria, "statusCodigo": status, "statusSigla": sigla, "tempoSegundos": tempo}
    return {"registrosEtapas": [
        reg(1, 101, "José", "H Adulto E", 0, "OK", 3806),
        reg(2, 102, "Antonia", "D Adulto N", 0, "OK", 1381),
        reg(3, 103, "Caio", "H Adulto E", 3, "NP", None),
        reg(5, 105, "Dani", "H Adulto E", 0, "OK", None),
        reg(6, 106, "Eva", "H Adulto E", 0, "OK", 3000),
    ]}


class TestRitmo(unittest.TestCase):
    def test_metade_do_segundo_sobe(self):
        # José Ronaldo, etapa 2 de 2026: 3806 s em 4000 m = 951,5 s/km; o site mostra 15'52".
        ritmo = calcularRitmoSegundosPorKm(3806, 4000)
        self.assertEqual(ritmo, 952)
        self.assertEqual(formatarRitmo(ritmo), "15'52\"")

    def test_empate_exato_pode_diferir_1s_do_site_e_fora_dele_coincide(self):
        # 2025, etapa 3, D Adulto B: 3735 s em 3600 m = 1037,5 s/km exatos; o site mostra 17'17" (desce),
        # a convenção do projeto sobe para 17'18". Divergência documentada na spec.
        self.assertEqual(formatarRitmo(calcularRitmoSegundosPorKm(3735, 3600)), "17'18\"")
        # Sem empate exato não há ambiguidade: 4300 m em 3340 s = 776,74 s/km.
        self.assertEqual(calcularRitmoSegundosPorKm(3340, 4300), 777)

    def test_casos_de_2026_conferidos_no_site(self):
        casos = (
            (3588, 6100, "9'48\""),    # etapa 1, H Adulto E
            (1381, 1500, "15'21\""),   # etapa 2, D Adulto N
            (5353, 5900, "15'07\""),   # etapa 3, D Adulto E
            (2869, 5700, "8'23\""),    # etapa 4, H Adulto E
        )
        for tempo, distancia, esperado in casos:
            with self.subTest(tempo=tempo, distancia=distancia):
                self.assertEqual(formatarRitmo(calcularRitmoSegundosPorKm(tempo, distancia)), esperado)

    def test_recusa_tempo_e_distancia_invalidos(self):
        for tempo, distancia in ((0, 4000), (-1, 4000), (3000, 0), (3000, -5)):
            with self.subTest(tempo=tempo, distancia=distancia), self.assertRaises(ValueError):
                calcularRitmoSegundosPorKm(tempo, distancia)

    def test_formata_minutos_e_segundos_com_zero_a_esquerda(self):
        self.assertEqual(formatarRitmo(367), "6'07\"")
        self.assertEqual(formatarRitmo(600), "10'00\"")


class TestMontarPercursos(unittest.TestCase):
    def test_zero_em_distancia_e_subida_vira_nulo_e_listas_saem_ordenadas(self):
        dados = montarPercursos(_bruto(), "Sintetico.mdb", HASH)
        porId = {p["percursoId"]: p for p in dados["percursos"]}
        self.assertIsNone(porId[30]["distanciaM"])
        self.assertIsNone(porId[20]["subidaM"])
        self.assertEqual(porId[10]["subidaM"], 110)
        self.assertEqual([p["percursoId"] for p in dados["percursos"]], [10, 20, 30])
        self.assertEqual([p["runnerPk"] for p in dados["participacoes"]], [1, 2, 3, 4])
        self.assertNotIn("statusCodigo", dados["participacoes"][0])

    def test_quem_nao_concluiu_pode_ficar_sem_percurso_ou_sem_distancia(self):
        dados = montarPercursos(_bruto(), "Sintetico.mdb", HASH)
        self.assertIsNone(dados["participacoes"][3]["percursoId"])

    def test_recusa_quem_concluiu_sem_percurso_com_percurso_inexistente_ou_sem_distancia(self):
        bruto = _bruto()
        bruto["participacoes"] = [
            {"competitionId": 36, "runnerPk": 7, "percursoId": None, "statusCodigo": 0,
             "horaLargada": None, "horaChegada": None},
            {"competitionId": 36, "runnerPk": 8, "percursoId": 999, "statusCodigo": 0,
             "horaLargada": None, "horaChegada": None},
            {"competitionId": 36, "runnerPk": 9, "percursoId": 30, "statusCodigo": 0,
             "horaLargada": None, "horaChegada": None},
        ]
        with self.assertRaises(EntradaInvalidaError) as ctx:
            montarPercursos(bruto, "Sintetico.mdb", HASH)
        mensagem = str(ctx.exception)
        self.assertIn("runnerPk 7: concluiu sem percurso", mensagem)
        self.assertIn("runnerPk 8: percurso 999 inexistente", mensagem)
        self.assertIn("runnerPk 9: percurso 30 sem distância", mensagem)


class TestValidarPercursos(unittest.TestCase):
    def _valido(self) -> dict[str, Any]:
        return montarPercursos(_bruto(), "Sintetico.mdb", HASH)

    def test_aceita_json_valido(self):
        validarDadosPercursos(self._valido())

    def test_recusa_campo_de_dado_pessoal(self):
        dados = self._valido()
        dados["participacoes"][0]["anoNascimento"] = 1980
        with self.assertRaises(EntradaInvalidaError):
            validarDadosPercursos(dados)

    def test_recusa_percurso_inexistente_nas_referencias(self):
        dados = self._valido()
        dados["categoriaPercurso"][0]["percursoId"] = 999
        with self.assertRaises(EntradaInvalidaError):
            validarDadosPercursos(dados)

    def test_recusa_fonte_com_pasta_e_hash_invalido(self):
        dados = self._valido()
        dados["fonte"] = "pasta/Sintetico.mdb"
        dados["sha256Fonte"] = "xyz"
        with self.assertRaises(EntradaInvalidaError) as ctx:
            validarDadosPercursos(dados)
        self.assertIn("fonte", str(ctx.exception))
        self.assertIn("sha256Fonte", str(ctx.exception))


class TestCalcularRitmos(unittest.TestCase):
    def test_liga_registro_ao_percurso_do_atleta_e_explica_quem_ficou_sem_ritmo(self):
        percursos = montarPercursos(_bruto(), "Sintetico.mdb", HASH)
        ritmos, semRitmo = calcularRitmos(_dadosEtapas(), percursos)

        porNome = {r.nome: r for r in ritmos}
        self.assertEqual(set(porNome), {"José", "Antonia"})
        self.assertEqual(porNome["José"].distanciaM, 4000)
        self.assertEqual(formatarRitmo(porNome["José"].ritmoSegundosPorKm), "15'52\"")
        self.assertEqual(formatarRitmo(porNome["Antonia"].ritmoSegundosPorKm), "15'21\"")

        motivos = {s.nome: s.motivo for s in semRitmo}
        self.assertEqual(motivos["Caio"], "não concluiu (NP)")
        self.assertEqual(motivos["Dani"], "sem tempo")
        self.assertEqual(motivos["Eva"], "sem percurso")

    def test_atleta_na_mesma_categoria_usa_o_proprio_percurso(self):
        percursos = montarPercursos(_bruto(), "Sintetico.mdb", HASH)
        percursos = copy.deepcopy(percursos)
        # Percurso do atleta 1 trocado para o de 1500 m: a distância segue o percurso do atleta, não a categoria.
        for p in percursos["participacoes"]:
            if p["runnerPk"] == 1:
                p["percursoId"] = 20
        ritmos, _ = calcularRitmos(_dadosEtapas(), percursos)
        self.assertEqual({r.nome: r.distanciaM for r in ritmos}["José"], 1500)


if __name__ == "__main__":
    unittest.main()
