# -*- coding: utf-8 -*-
"""Testes da ingestão da planilha do site de resultados do Helga e da mesclagem com o JSON do banco."""
import datetime as dt
import json
import os
import tempfile
import unittest
from typing import Any

from openpyxl import Workbook

from src.extracaoAccess.leitorHelgaWeb import (
    extrairComplemento,
    registrarNoManifesto,
    resolverTempoSegundos,
)
from src.extracaoAccess.mesclarComplemento import carregarDadosDoAno, mesclarComplemento
from src.extracaoAccess.validarEntrada import EntradaInvalidaError, validarDadosHelga

HASH = "a" * 64
FLAG = "\U0001f1e7\U0001f1f7\xa0"


def _base() -> dict[str, Any]:
    perfil = {"clubeId": 1, "clubeSigla": "AAA", "clubeNome": "Clube A", "clubeFiliadoCBO": True, "sexo": 1}
    reg = {
        "competitionId": 37, "runnerPk": 1, "cbo": 1, "nome": "Ana", "sexo": 1, "clubeId": 1, "clubeSigla": "AAA",
        "clubeNome": "Clube A", "clubeFiliadoCBO": True, "categoriaId": 7, "categoria": "H Adulto A",
        "statusCodigo": 3, "statusSigla": "NP", "classifyYN": True, "tempo": None, "tempoSegundos": None,
        "tempoMs": 0, "etapa": 3,
    }
    nomes = ((1, "Ana"), (2, "Beto"), (3, "Caio"), (4, "Dani"))
    return {
        "fonte": "Sintetico.mdb", "sha256Fonte": "0" * 64,
        "etapas": [{"numeroEtapa": 1, "competitionId": 36, "data": "2025-05-25"},
                   {"numeroEtapa": 3, "competitionId": 37, "data": "2025-08-17"}],
        "clubes": [
            {"clubeId": 1, "sigla": "AAA", "nome": "Clube A", "filiadoCBO": True},
            {"clubeId": 2, "sigla": "IND", "nome": "Indiv.", "filiadoCBO": False},
        ],
        "perfisAtletas": {str(c): {"cbo": c, "nome": n, **perfil} for c, n in nomes},
        "registrosEtapas": [dict(reg), {**reg, "etapa": 1, "competitionId": 36, "statusCodigo": 0, "statusSigla": "OK"}],
    }


def _linhasLista(inscritos: list[tuple[int, str, str, str]]) -> list[tuple[Any, ...]]:
    """Lista de partida: `(cbo, nome, categoria, clube)` agrupado por clube."""
    linhas: list[tuple[Any, ...]] = []
    for clube in dict.fromkeys(c for *_, c in inscritos):
        grupo = [i for i in inscritos if i[3] == clube]
        linhas.append((f"{clube} ({len(grupo)})", None, None, None, None, None, None))
        for cbo, nome, cat, _ in grupo:
            linhas.append((cbo, FLAG, nome, "BRA", f"#{1000 + cbo}#", dt.time(8, 0), cat))
    return linhas


def _planilha(pasta: str, resultados: list[tuple[Any, ...]], inscritos: list[tuple[int, str, str, str]], etapa: int = 2) -> str:
    wb = Workbook()
    wsL = wb.active
    assert wsL is not None
    wsL.title = f"listaPartidaEtapa{etapa}"
    for linha in _linhasLista(inscritos):
        wsL.append(linha)
    wsR = wb.create_sheet(f"resultadoEtapa{etapa}")
    for linha in resultados:
        wsR.append(linha)
    caminho = os.path.join(pasta, "exportadoSiteHelga.xlsx")
    wb.save(caminho)
    return caminho


CAB = ("H Adulto A\xa0(4)\xa0length\xa03000m\xa0climb\xa040m", None, None, None, None, None, None, None, None)
SUB = (None, None, None, None, None, None, "[H:]M:S", "min/km", None)
RESULTADOS = [
    CAB, SUB,
    ("1.", FLAG, "Ana", 1, "BRA", "Clube A", dt.timedelta(hours=30), "10'00\"", None),   # 30:00 lido como 30h
    ("2.", FLAG, "Beto", 2, "BRA", "Clube A", dt.time(1, 5, 0), "21'40\"", "+35:00"),     # 1:05:00 de verdade
    ("NCL", FLAG, "Caio", 3, "BRA", "Clube A", None, None, None),
    ("OT", FLAG, "Dani", 4, "BRA", "Clube A", None, None, None),
]
INSCRITOS = [
    (1, "Ana", "H Adulto A", "Clube A"), (2, "Beto", "H Adulto A", "Clube A"), (3, "Caio", "H Adulto A", "Clube A"),
    (4, "Dani", "H Adulto A", "Clube A"), (5, "Edu", "H Adulto A", "Clube A"),
    (900, "Militar", "Militar Alfa", "Indiv."),
]
ETAPA2 = {2: {"numeroEtapa": 2, "competitionId": 6071, "data": "2025-06-29", "local": "L", "clubeOrganizadorSigla": "AAA"}}


class TestTempo(unittest.TestCase):
    def test_mmss_lido_como_hora_minuto_e_hmmss_verdadeiro(self):
        self.assertEqual(resolverTempoSegundos(dt.time(21, 46), "27'12\"", 800), 1306)                       # 21:46
        self.assertEqual(resolverTempoSegundos(dt.timedelta(days=1, seconds=48480), "12'05\"", 3100), 2248)  # 37:28
        self.assertEqual(resolverTempoSegundos(dt.time(1, 8, 51), "18'36\"", 3700), 4131)                    # 1:08:51
        self.assertEqual(resolverTempoSegundos(dt.time(1, 30, 0), "30'00\"", 3000), 5400)                    # h:mm:ss, segundos 0

    def test_sem_leitura_unica_ou_sem_minkm_nao_ha_tempo(self):
        self.assertIsNone(resolverTempoSegundos(dt.time(1, 8, 51), "18'36\"", 1000))   # nenhuma leitura bate
        self.assertIsNone(resolverTempoSegundos(dt.time(21, 46), None, 800))


class TestExtracao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)

    def _extrair(self, resultados=None, inscritos=None, base=None, etapas=None, alias=None):
        caminho = _planilha(self.pasta.name, resultados or RESULTADOS, inscritos or INSCRITOS)
        return extrairComplemento(caminho, 2025, base or _base(), ETAPA2 if etapas is None else etapas, HASH, alias)

    def test_situacao_de_cada_inscrito_e_atleta_novo(self):
        complemento, avisos = self._extrair()
        regs = {r["cbo"]: r for r in complemento["registrosEtapas"]}
        self.assertEqual(sorted(regs), [1, 2, 3, 4, 5])   # o militar fica de fora
        self.assertEqual((regs[1]["statusSigla"], regs[1]["tempo"], regs[1]["tempoSegundos"]), ("OK", "00:30:00", 1800))
        self.assertEqual((regs[2]["statusSigla"], regs[2]["tempo"]), ("OK", "01:05:00"))
        self.assertEqual((regs[3]["statusCodigo"], regs[3]["statusSigla"]), (1, "NC"))
        self.assertEqual((regs[4]["statusCodigo"], regs[4]["statusSigla"]), (5, "OT"))
        self.assertEqual((regs[5]["statusCodigo"], regs[5]["statusSigla"]), (3, "NP"))   # inscrito que não largou
        self.assertEqual(complemento["etapas"][0]["numeroEtapa"], 2)
        self.assertEqual(list(complemento["perfisAtletas"]), ["5"])   # só o atleta fora do cadastro
        self.assertEqual(complemento["fonte"], "exportadoSiteHelga.xlsx")
        self.assertEqual(avisos, [])
        validarDadosHelga(complemento)

    def test_etapa_com_banco_mantem_os_metadados_do_banco(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        caminho = _planilha(pasta.name, RESULTADOS, INSCRITOS, etapa=3)
        complemento, _ = extrairComplemento(caminho, 2025, _base(), {}, HASH)
        self.assertEqual(complemento["etapas"][0]["competitionId"], 37)
        self.assertTrue(all(r["competitionId"] == 37 and r["etapa"] == 3 for r in complemento["registrosEtapas"]))

    def test_recusas_listam_o_problema(self):
        foraDaLista = ("NCL", FLAG, "Zé", 77, "BRA", "Clube A", None, None, None)
        tempoRuim = ("1.", FLAG, "Ana", 1, "BRA", "Clube A", dt.time(0, 45, 0), "10'00\"", None)
        rankErrado = ("2.", FLAG, "Ana", 1, "BRA", "Clube A", dt.timedelta(hours=30), "10'00\"", None)
        casos = {
            "resultado fora da lista de partida": (
                [*RESULTADOS[:-2], foraDaLista, RESULTADOS[-1]], INSCRITOS, "ausente da lista de partida"),
            "tempo incompatível com min/km": ([CAB, SUB, tempoRuim, *RESULTADOS[3:]], INSCRITOS, "sem leitura única"),
            "colocação fora de sequência": ([CAB, SUB, rankErrado, *RESULTADOS[3:]], INSCRITOS, "na posição 1"),
            "contagem do cabeçalho": (RESULTADOS[:-1], INSCRITOS, "cabeçalho diz 4, lidos 3"),
            "clube desconhecido": (
                RESULTADOS, [(1, "Ana", "H Adulto A", "Clube Fantasma"), *INSCRITOS[1:]], "ausente da tabela de clubes"),
        }
        for nome, (resultados, inscritos, trecho) in casos.items():
            with self.subTest(nome), self.assertRaises(EntradaInvalidaError) as ctx:
                self._extrair(resultados, inscritos)
            self.assertIn(trecho, str(ctx.exception))

    def test_diferenca_para_o_lider_divergente_e_recusada(self):
        beto = ("2.", FLAG, "Beto", 2, "BRA", "Clube A", dt.time(1, 5, 0), "21'40\"", "+34:00")
        with self.assertRaises(EntradaInvalidaError) as ctx:
            self._extrair([*RESULTADOS[:3], beto, *RESULTADOS[4:]])
        self.assertIn("diferença do site", str(ctx.exception))

    def test_etapa_nova_sem_metadados_e_recusada(self):
        with self.assertRaises(EntradaInvalidaError) as ctx:
            self._extrair(etapas={})
        self.assertIn("--etapa-nova", str(ctx.exception))

    def test_alias_de_clube_resolve_nome_diferente_no_site(self):
        inscritos = [(c, n, k, "Clube A Longo") for c, n, k, _ in INSCRITOS[:5]]
        complemento, _ = self._extrair(inscritos=inscritos, alias={"Clube A Longo": "AAA"})
        self.assertEqual({r["clubeSigla"] for r in complemento["registrosEtapas"]}, {"AAA"})
        with self.assertRaises(EntradaInvalidaError):
            self._extrair(inscritos=inscritos, alias={"Clube A Longo": "XXX"})

    def test_empate_de_tempo_gera_aviso(self):
        beto = ("2.", FLAG, "Beto", 2, "BRA", "Clube A", dt.timedelta(hours=30), "10'00\"", "+0:00")
        _, avisos = self._extrair([*RESULTADOS[:3], beto, *RESULTADOS[4:]])
        self.assertTrue(any("mesmo tempo" in a for a in avisos))


class TestManifestoEMesclagem(unittest.TestCase):
    def test_congelamento_no_manifesto(self):
        with tempfile.TemporaryDirectory() as pasta:
            with open(os.path.join(pasta, "arquivosCongelados.sha256"), "w", encoding="utf-8") as fh:
                fh.write("# cabecalho\n")
            self.assertEqual(registrarNoManifesto(pasta, 2025, "exportadoSiteHelga.xlsx", HASH), "novo")
            self.assertEqual(registrarNoManifesto(pasta, 2025, "exportadoSiteHelga.xlsx", HASH), "já registrado")
            with self.assertRaises(EntradaInvalidaError):
                registrarNoManifesto(pasta, 2025, "exportadoSiteHelga.xlsx", "b" * 64)

    def test_complemento_substitui_a_etapa_do_banco(self):
        with tempfile.TemporaryDirectory() as pasta:
            complemento, _ = extrairComplemento(_planilha(pasta, RESULTADOS, INSCRITOS, etapa=3), 2025, _base(), {}, HASH)
            mesclado = mesclarComplemento(_base(), complemento)
        self.assertEqual([e["numeroEtapa"] for e in mesclado["etapas"]], [1, 3])
        etapa3 = [r for r in mesclado["registrosEtapas"] if r["etapa"] == 3]
        self.assertEqual(sorted(r["cbo"] for r in etapa3), [1, 2, 3, 4, 5])
        self.assertEqual(len([r for r in mesclado["registrosEtapas"] if r["etapa"] == 1]), 1)   # etapa 1 intacta
        self.assertEqual(mesclado["fonte"], "Sintetico.mdb")
        self.assertIn("5", mesclado["perfisAtletas"])
        validarDadosHelga(mesclado)

    def test_carregar_dados_do_ano_confere_hash_de_cada_arquivo(self):
        with tempfile.TemporaryDirectory() as raiz:
            pastaExtraidos = os.path.join(raiz, "2025", "extraidos")
            os.makedirs(pastaExtraidos)
            base = _base()
            complemento, _ = extrairComplemento(_planilha(raiz, RESULTADOS, INSCRITOS, etapa=3), 2025, base, {}, HASH)
            for nome, dados in (("etapasHelga2025.json", base), ("etapasHelgaWeb2025.json", complemento)):
                with open(os.path.join(pastaExtraidos, nome), "w", encoding="utf-8") as fh:
                    json.dump(dados, fh)
            manifesto = os.path.join(raiz, "arquivosCongelados.sha256")
            with open(manifesto, "w", encoding="utf-8") as fh:
                fh.write(f"{'0' * 64}  2025/Sintetico.mdb\n")
            with self.assertRaises(EntradaInvalidaError):   # planilha ainda não congelada
                carregarDadosDoAno(2025, raiz)
            with open(manifesto, "a", encoding="utf-8") as fh:
                fh.write(f"{HASH}  2025/exportadoSiteHelga.xlsx\n")
            dados, usados = carregarDadosDoAno(2025, raiz)
        self.assertEqual(usados, ["etapasHelga2025.json", "etapasHelgaWeb2025.json"])
        self.assertEqual([e["numeroEtapa"] for e in dados["etapas"]], [1, 3])


if __name__ == "__main__":
    unittest.main()
