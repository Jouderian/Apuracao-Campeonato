# -*- coding: utf-8 -*-
"""Testes de segurança: validação das entradas, dados pessoais, injeção no PowerShell, empates e fuzz."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
    TEM_HYPOTHESIS = True
except ImportError:
    TEM_HYPOTHESIS = False

    def given(*args, **kwargs):
        return lambda f: f

    def settings(*args, **kwargs):
        return lambda f: f

    class _MockSt:
        def __getattr__(self, name):
            return lambda *a, **kw: _MockSt()

        def __or__(self, other):
            return _MockSt()

        def __ror__(self, other):
            return _MockSt()

    st = _MockSt()

from src.extracaoAccess import extrairHelga
from src.extracaoAccess.leitorVoluntarios import lerVoluntariosMarkdown
from src.extracaoAccess.validarEntrada import (
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosHelga,
)
from src.motorCalculo.pontuacao import apurarCampeonatoCCO
from src.relatorios.geradorExcelPdf import sanitizarCelulaExcel
from src.relatorios.geradorMarkdown import gerarRelatorioIndividualMarkdown
from tests.test_apuracao_integracao import CATEGORIA, _registro, montarDadosSinteticos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DADOS = os.path.join(RAIZ, "Dados")


def _dadosReais2026() -> dict:
    with open(os.path.join(PASTA_DADOS, "2026", "extraidos", "etapasHelga2026.json"), encoding="utf-8") as fh:
        return json.load(fh)


class TestValidarEntrada(unittest.TestCase):
    def test_json_real_de_2026_e_valido_e_confere_no_manifesto(self):
        dados = _dadosReais2026()
        validarDadosHelga(dados)
        conferirHashNoManifesto(dados, 2026, PASTA_DADOS)

    def test_recusa_ano_de_nascimento_no_registro_e_no_perfil(self):
        for onde in ("registrosEtapas", "perfisAtletas"):
            dados = copy.deepcopy(_dadosReais2026())
            alvo = dados[onde][0] if onde == "registrosEtapas" else next(iter(dados[onde].values()))
            alvo["anoNascimento"] = 1990
            with self.assertRaisesRegex(EntradaInvalidaError, "anoNascimento"):
                validarDadosHelga(dados)

    def test_recusa_outros_campos_de_dados_pessoais(self):
        for campo in ("cpf", "email", "Birthdate", "telefone"):
            dados = copy.deepcopy(_dadosReais2026())
            dados["registrosEtapas"][0][campo] = "x"
            with self.assertRaises(EntradaInvalidaError, msg=campo):
                validarDadosHelga(dados)

    def test_recusa_campo_obrigatorio_ausente_e_tipo_errado(self):
        dados = copy.deepcopy(_dadosReais2026())
        del dados["registrosEtapas"][0]["cbo"]
        dados["registrosEtapas"][1]["statusCodigo"] = "0"
        dados["registrosEtapas"][2]["classifyYN"] = 1  # bool não aceita inteiro
        with self.assertRaises(EntradaInvalidaError) as ctx:
            validarDadosHelga(dados)
        mensagem = str(ctx.exception)
        self.assertIn("cbo", mensagem)
        self.assertIn("statusCodigo", mensagem)
        self.assertIn("classifyYN", mensagem)

    def test_recusa_hash_malformado_fonte_com_pasta_e_estrutura_invalida(self):
        base = _dadosReais2026()
        for campo, valor in (("sha256Fonte", "ABC"), ("fonte", "../x.mdb"), ("etapas", {})):
            dados = copy.deepcopy(base)
            dados[campo] = valor
            with self.assertRaises(EntradaInvalidaError, msg=campo):
                validarDadosHelga(dados)
        with self.assertRaises(EntradaInvalidaError):
            validarDadosHelga([])

    def test_recusa_texto_com_caractere_de_controle_ou_longo_demais(self):
        for valor in ("Ana\n| injetado |", "A" * 500):
            dados = copy.deepcopy(_dadosReais2026())
            dados["registrosEtapas"][0]["nome"] = valor
            with self.assertRaises(EntradaInvalidaError):
                validarDadosHelga(dados)

    def test_recusa_registro_de_etapa_inexistente(self):
        dados = copy.deepcopy(_dadosReais2026())
        dados["registrosEtapas"][0]["etapa"] = 99
        with self.assertRaisesRegex(EntradaInvalidaError, "inexistente"):
            validarDadosHelga(dados)

    def test_hash_divergente_ou_ausente_do_manifesto_e_recusado(self):
        dados = copy.deepcopy(_dadosReais2026())
        dados["sha256Fonte"] = "0" * 64
        with self.assertRaisesRegex(EntradaInvalidaError, "diverge"):
            conferirHashNoManifesto(dados, 2026, PASTA_DADOS)
        with self.assertRaisesRegex(EntradaInvalidaError, "ausente"):
            conferirHashNoManifesto(_dadosReais2026(), 2099, PASTA_DADOS)
        with tempfile.TemporaryDirectory() as vazia:
            with self.assertRaisesRegex(EntradaInvalidaError, "manifesto ausente"):
                conferirHashNoManifesto(_dadosReais2026(), 2026, vazia)


class TestExtracaoPowerShell(unittest.TestCase):
    CAMINHO_HOSTIL = r"C:\Dados\a$(New-Item -ItemType File -Path C:\pwned.txt)`;'}.mdb"

    def test_caminho_do_banco_vai_por_ambiente_e_nunca_dentro_do_script(self):
        with mock.patch.object(extrairHelga.subprocess, "run") as falso:
            falso.return_value = mock.Mock(stdout="{}")
            extrairHelga.extrairDadosViaPowerShellOdbc(self.CAMINHO_HOSTIL)
        argumentos = falso.call_args.args[0]
        ambiente = falso.call_args.kwargs["env"]
        self.assertNotIn("pwned", " ".join(argumentos))
        self.assertIn("pwned", ambiente["CCO_MDB_CAMINHO"])
        self.assertIn("$env:CCO_MDB_CAMINHO", argumentos[-1])
        # Caminho do Windows PowerShell em disco, nunca o nome solto resolvido pelo PATH.
        self.assertTrue(argumentos[0].lower().endswith("powershell.exe"))
        self.assertNotEqual(argumentos[0].lower(), "powershell.exe")
        self.assertIn("System32", argumentos[0])
        self.assertFalse(falso.call_args.kwargs.get("shell", False))

    def test_script_nao_extrai_data_nem_ano_de_nascimento(self):
        with mock.patch.object(extrairHelga.subprocess, "run") as falso:
            falso.return_value = mock.Mock(stdout="{}")
            extrairHelga.extrairDadosViaPowerShellOdbc("x.mdb")
        script = falso.call_args.args[0][-1].lower()
        for proibido in ("birth", "yearofbirth", "anonascimento"):
            self.assertNotIn(proibido, script)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell do Windows")
    def test_nome_de_arquivo_com_subexpressao_nao_executa_comando(self):
        with tempfile.TemporaryDirectory() as pasta:
            marcador = os.path.join(pasta, "marcador.txt")
            caminho = os.path.join(pasta, f"a$(New-Item -ItemType File -Path {marcador}).mdb")
            with self.assertRaises((subprocess.CalledProcessError, OSError)):  # banco inexistente: só a conexão falha
                extrairHelga.extrairDadosViaPowerShellOdbc(caminho)
            self.assertFalse(os.path.exists(marcador))


class TestEmpateNaoResolvido(unittest.TestCase):
    def _dadosComEmpate(self) -> tuple[dict, dict]:
        dadosHelga, dadosVoluntarios = montarDadosSinteticos()
        dadosVoluntarios["voluntarios"] = []
        for etapa in (1, 2, 3, 4):  # Dani e Edu: não classificados em todas as etapas (1 ponto cada)
            for cbo, nome in ((4, "Dani"), (5, "Edu")):
                reg = _registro(etapa, cbo, nome, 0)
                reg.update({"statusCodigo": 1, "statusSigla": "NC", "tempo": None, "tempoSegundos": None})
                dadosHelga["registrosEtapas"].append(reg)
        return dadosHelga, dadosVoluntarios

    def test_empate_em_todos_os_criterios_e_sinalizado_sem_usar_idade(self):
        resultado = apurarCampeonatoCCO(*self._dadosComEmpate())
        fichas = {f.cbo: f for f in resultado["fichasPorCategoria"][CATEGORIA]}
        self.assertTrue(fichas[4].empateNaoResolvido and fichas[5].empateNaoResolvido)
        self.assertFalse(fichas[1].empateNaoResolvido)
        self.assertLess(fichas[4].colocacaoNaCategoria, fichas[5].colocacaoNaCategoria)  # ordem estável por CBO
        markdown = gerarRelatorioIndividualMarkdown(2026, "XX CCO", resultado)
        self.assertIn("Empate não resolvido", markdown)
        self.assertIn("CBO 4, 5", markdown)

    def test_sem_empate_nada_e_sinalizado(self):
        resultado = apurarCampeonatoCCO(*montarDadosSinteticos())
        self.assertFalse(any(f.empateNaoResolvido for f in resultado["fichasPorCategoria"][CATEGORIA]))
        self.assertNotIn("Empate não resolvido", gerarRelatorioIndividualMarkdown(2026, "XX CCO", resultado))

    def test_json_sintetico_com_ano_de_nascimento_nao_entra_no_motor_validado(self):
        dados = _dadosReais2026()
        dados["registrosEtapas"][0]["anoNascimento"] = 1990
        with self.assertRaises(EntradaInvalidaError):
            validarDadosHelga(dados)


@unittest.skipUnless(TEM_HYPOTHESIS, "hypothesis não está instalado")
class TestFuzz(unittest.TestCase):
    @settings(max_examples=300, deadline=None)
    @given(st.text())
    def test_sanitizar_celula_excel_nunca_deixa_formula_no_inicio(self, texto):
        saida = sanitizarCelulaExcel(texto)
        self.assertFalse(saida.startswith(("=", "+", "-", "@")))

    @settings(max_examples=300, deadline=None)
    @given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=400))
    def test_leitor_de_voluntarios_aceita_qualquer_texto_sem_falhar(self, texto):
        resultado = lerVoluntariosMarkdown(texto)
        self.assertEqual(set(resultado), {"voluntarios", "arbitros", "penalidadesArt23", "unificacoesCbo"})

    @settings(max_examples=100, deadline=None)
    @given(st.text(alphabet="0123456789", min_size=1, max_size=5000))
    def test_leitor_de_voluntarios_nao_converte_numeros_enormes(self, digitos):
        resultado = lerVoluntariosMarkdown(f"| 1ª | {digitos} | Nome |")
        for v in resultado["voluntarios"]:
            self.assertLess(v["cbo"], 10**9)

    @settings(max_examples=200, deadline=None)
    @given(st.recursive(
        st.none() | st.booleans() | st.integers() | st.text(max_size=30),
        lambda filho: st.lists(filho, max_size=4) | st.dictionaries(st.text(max_size=12), filho, max_size=4),
        max_leaves=20,
    ))
    def test_validador_so_levanta_entrada_invalida_em_qualquer_json(self, dados):
        try:
            validarDadosHelga(dados)
        except EntradaInvalidaError:
            pass


if __name__ == "__main__":
    unittest.main()
