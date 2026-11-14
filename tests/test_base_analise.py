# -*- coding: utf-8 -*-
"""Testes da Camada C da análise de desempenho: geração da base SQLite, consulta somente leitura e dicionário."""
import os
import re
import sqlite3
import tempfile
import unittest
from typing import Any

from src.analises.consultar import ConsultaRecusadaError, consultar, normalizarConsulta
from src.analises.gerarBase import DadosAno, construirBase, etapasApenasDoBanco, semCategoriasNaoCompetitivas
from src.extracaoAccess.extrairParciais import montarParciais
from src.extracaoAccess.extrairPercursos import montarPercursos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_DICIONARIO = os.path.join(RAIZ, ".agents", "wiki", "dicionario-dados-analise.md")
HASH = "a" * 64


def _registro(runnerPk: int, cbo: int, nome: str, categoria: str, status: int, sigla: str,
              tempo: int | None, etapa: int = 2, competitionId: int = 36) -> dict[str, Any]:
    return {
        "etapa": etapa, "competitionId": competitionId, "runnerPk": runnerPk, "cbo": cbo, "nome": nome,
        "clubeSigla": "AAA", "categoria": categoria, "statusCodigo": status, "statusSigla": sigla,
        "tempoSegundos": tempo,
    }


def _dadosAno() -> DadosAno:
    etapas: dict[str, Any] = {
        "etapas": [
            {"numeroEtapa": 2, "competitionId": 36, "data": "2026-06-28", "local": "Água Verde",
             "clubeOrganizadorSigla": "COFORT"},
            {"numeroEtapa": 3, "competitionId": 37, "data": "2026-08-30", "local": "Pici"},
        ],
        "registrosEtapas": [
            _registro(1, 101, "José", "H Adulto E", 0, "OK", 600),
            _registro(2, 102, "Antonia", "D Adulto N", 0, "OK", 1381),
            _registro(3, 103, "Caio", "H Adulto E", 3, "NP", None),
            _registro(9, 109, "Outro", "H Adulto E", 0, "OK", 500, etapa=3, competitionId=37),
        ],
    }
    percursos = montarPercursos({
        "percursos": [
            {"percursoId": 10, "competitionId": 36, "numero": 1, "nome": "", "distanciaM": 1000, "subidaM": 20},
            {"percursoId": 20, "competitionId": 36, "numero": 2, "nome": "", "distanciaM": 1500, "subidaM": 0},
        ],
        "categoriaPercurso": [],
        "participacoes": [
            {"competitionId": 36, "runnerPk": 1, "percursoId": 10, "statusCodigo": 0, "categoria": "H Adulto E",
             "horaLargada": None, "horaChegada": None},
            {"competitionId": 36, "runnerPk": 2, "percursoId": 20, "statusCodigo": 0, "categoria": "D Adulto N",
             "horaLargada": None, "horaChegada": None},
            {"competitionId": 36, "runnerPk": 3, "percursoId": 10, "statusCodigo": 3, "categoria": "H Adulto E",
             "horaLargada": None, "horaChegada": None},
        ],
    }, "Sintetico.mdb", HASH)
    parciais = montarParciais({
        "postos": [
            {"percursoId": 10, "ordem": 1, "codigoPosto": 31, "distanciaM": 400},
            {"percursoId": 10, "ordem": 2, "codigoPosto": 999, "distanciaM": 600},
        ],
        "concluintes": [
            {"competitionId": 36, "runnerPk": 1, "percursoId": 10, "chip": 111, "tempo": "00:10:00",
             "categoria": "H Adulto E"},
            {"competitionId": 36, "runnerPk": 2, "percursoId": 20, "chip": 222, "tempo": "00:23:01",
             "categoria": "D Adulto N"},
        ],
        "leituras": [
            {"leituraId": 1, "competitionId": 36, "chip": 111},
            {"leituraId": 2, "competitionId": 36, "chip": 222},
        ],
        "passagens": [
            {"leituraId": 1, "ordem": 1, "codigoPosto": 31, "tempoParcialSegundos": 240},
            {"leituraId": 1, "ordem": 2, "codigoPosto": 999, "tempoParcialSegundos": 360},
            {"leituraId": 2, "ordem": 1, "codigoPosto": 31, "tempoParcialSegundos": 100},   # soma não fecha
        ],
    }, "Sintetico.mdb", HASH)
    return DadosAno(ano=2026, etapas=etapas, percursos=percursos, parciais=parciais,
                    fontes=[("etapasHelga2026.json", HASH)])


class BaseTemporaria(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self._pasta.cleanup)
        self.caminho = os.path.join(self._pasta.name, "base.sqlite")
        construirBase(self.caminho, [_dadosAno()])


class TestGerarBase(BaseTemporaria):
    def test_participacao_tem_ritmo_percurso_do_atleta_e_motivo_de_quem_nao_tem(self):
        colunas, linhas, _ = consultar(
            self.caminho, "SELECT nome, distanciaM, ritmoSegundosPorKm, ritmoTexto, motivoSemRitmo "
                          "FROM participacao WHERE numeroEtapa = 2 ORDER BY runnerPk")
        porNome = {linha[0]: dict(zip(colunas, linha, strict=True)) for linha in linhas}
        self.assertEqual(porNome["José"]["ritmoSegundosPorKm"], 600)            # 600 s em 1 km
        self.assertEqual(porNome["José"]["ritmoTexto"], "10'00\"")
        self.assertEqual(porNome["Antonia"]["ritmoTexto"], "15'21\"")           # 1381 s em 1,5 km
        self.assertIsNone(porNome["Caio"]["ritmoSegundosPorKm"])
        self.assertEqual(porNome["Caio"]["motivoSemRitmo"], "não concluiu (NP)")

    def test_etapa_sem_percurso_no_ano_fica_sem_ritmo_com_motivo(self):
        _, linhas, _ = consultar(self.caminho, "SELECT motivoSemRitmo FROM participacao WHERE numeroEtapa = 3")
        self.assertEqual(linhas, [("sem percurso",)])

    def test_parciais_com_ritmo_por_trecho_e_ocorrencias(self):
        _, linhas, _ = consultar(
            self.caminho, "SELECT ordem, codigoPosto, distanciaM, ritmoTexto FROM vwRitmoTrecho "
                          "WHERE cbo = 101 ORDER BY ordem")
        self.assertEqual(linhas, [(1, 31, 400, "10'00\""), (2, 999, 600, "10'00\"")])
        _, ocorrencias, _ = consultar(self.caminho, "SELECT runnerPk, motivo FROM ocorrenciaParcial")
        self.assertEqual(ocorrencias, [(2, "soma das parciais (100 s) diverge do tempo oficial (1381 s)")])

    def test_vwritmo_so_traz_quem_tem_ritmo_e_a_base_sai_reproduzivel(self):
        _, linhas, _ = consultar(self.caminho, "SELECT nome FROM vwRitmo ORDER BY nome")
        self.assertEqual(linhas, [("Antonia",), ("José",)])
        outro = os.path.join(os.path.dirname(self.caminho), "outra.sqlite")
        construirBase(outro, [_dadosAno()])
        with open(self.caminho, "rb") as a, open(outro, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_etapas_apuradas_pela_planilha_ficam_fora(self):
        dados = _dadosAno().etapas
        sobra = etapasApenasDoBanco(dados, {3})
        self.assertEqual([e["numeroEtapa"] for e in sobra["etapas"]], [2])
        self.assertEqual({r["etapa"] for r in sobra["registrosEtapas"]}, {2})

    def test_categorias_nao_competitivas_ficam_fora_da_base(self):
        dados = {"registrosEtapas": [_registro(1, 101, "Ana", "H Adulto E", 0, "OK", 600),
                                     _registro(2, 102, "Bia", "DN1", 0, "OK", 300),
                                     _registro(3, 103, "Caio", "hn3", 0, "OK", 300),
                                     _registro(4, 104, "Duda", "Aberto D", 0, "OK", 400)]}
        restantes = semCategoriasNaoCompetitivas(dados)["registrosEtapas"]
        self.assertEqual([r["nome"] for r in restantes], ["Ana"])

    def test_base_nao_guarda_dado_pessoal_alem_de_nome_e_cbo(self):
        conn = sqlite3.connect(self.caminho)
        try:
            colunas = {
                linha[1].lower() for tabela in ("participacao", "parcial", "percurso", "etapa")
                for linha in conn.execute(f"PRAGMA table_info({tabela})")   # nosec B608 - nomes fixos do teste
            }
        finally:
            conn.close()
        for proibida in ("anonascimento", "datanascimento", "cpf", "email", "telefone", "endereco", "chip"):
            self.assertNotIn(proibida, colunas)


class TestConsultar(BaseTemporaria):
    def test_so_aceita_select_ou_with(self):
        for sql in ("INSERT INTO etapa (ano) VALUES (1)", "DROP TABLE participacao", "DELETE FROM participacao",
                    "UPDATE participacao SET nome = 'x'", "PRAGMA table_info(etapa)", "ATTACH 'x.db' AS x", ""):
            with self.subTest(sql=sql), self.assertRaises(ConsultaRecusadaError):
                consultar(self.caminho, sql)

    def test_recusa_mais_de_uma_instrucao_e_escrita_escondida_em_with(self):
        with self.assertRaises((ConsultaRecusadaError, sqlite3.Error)):
            consultar(self.caminho, "SELECT 1; DROP TABLE participacao")
        with self.assertRaises(sqlite3.Error):
            consultar(self.caminho, "WITH x AS (SELECT 1) DELETE FROM participacao")
        _, linhas, _ = consultar(self.caminho, "SELECT COUNT(*) FROM participacao")
        self.assertEqual(linhas, [(4,)])

    def test_base_aberta_so_para_leitura(self):
        # Mesmo contornando o autorizador, a base abre com mode=ro: a escrita falha.
        from src.analises.consultar import abrirSomenteLeitura
        conn = abrirSomenteLeitura(self.caminho)
        try:
            conn.set_authorizer(None)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM participacao")
        finally:
            conn.close()

    def test_limite_trunca_e_avisa(self):
        _, linhas, truncado = consultar(self.caminho, "SELECT nome FROM participacao", limite=2)
        self.assertEqual(len(linhas), 2)
        self.assertTrue(truncado)
        _, linhas, truncado = consultar(self.caminho, "SELECT nome FROM participacao", limite=10)
        self.assertEqual(len(linhas), 4)
        self.assertFalse(truncado)

    def test_limite_fora_da_faixa_e_base_inexistente(self):
        for limite in (0, 5001):
            with self.subTest(limite=limite), self.assertRaises(ConsultaRecusadaError):
                consultar(self.caminho, "SELECT 1", limite=limite)
        with self.assertRaises(FileNotFoundError):
            consultar(os.path.join(os.path.dirname(self.caminho), "nao-existe.sqlite"), "SELECT 1")

    def test_consulta_longa_demais_e_interrompida(self):
        with self.assertRaises(sqlite3.Error):
            consultar(self.caminho, "WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) "
                                    "SELECT COUNT(*) FROM c", limite=1)

    def test_normalizar_remove_ponto_e_virgula_final(self):
        self.assertEqual(normalizarConsulta("  select 1 ; "), "select 1")


class TestDicionario(BaseTemporaria):
    """O dicionário de dados precisa cobrir todas as tabelas e colunas da base."""

    def _documentado(self) -> dict[str, set[str]]:
        with open(CAMINHO_DICIONARIO, encoding="utf-8") as fh:
            texto = fh.read()
        secoes = re.split(r"^### `", texto, flags=re.MULTILINE)[1:]
        documentado: dict[str, set[str]] = {}
        for secao in secoes:
            nome = secao.split("`", 1)[0]
            documentado[nome] = set(re.findall(r"^\| `(\w+)` \|", secao, flags=re.MULTILINE))
        return documentado

    def test_todas_as_tabelas_visoes_e_colunas_estao_documentadas(self):
        documentado = self._documentado()
        conn = sqlite3.connect(self.caminho)
        try:
            objetos = [linha[0] for linha in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'")]
            for objeto in objetos:
                with self.subTest(objeto=objeto):
                    self.assertIn(objeto, documentado, f"{objeto} sem seção no dicionário")
                    colunas = {linha[1] for linha in conn.execute(f"PRAGMA table_info({objeto})")}   # nosec B608
                    self.assertEqual(colunas, documentado[objeto], f"colunas de {objeto} divergem do dicionário")
        finally:
            conn.close()
        self.assertEqual(set(documentado) - set(objetos), set(), "seção do dicionário sem objeto na base")


if __name__ == "__main__":
    unittest.main()
