#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gera a base SQLite de análise de desempenho a partir dos JSON higienizados (ADR-009).

A base é derivada e reconstruível: fica fora do Git e nunca é editada à mão. Lê só os JSON de
Dados/<ano>/extraidos/ (nunca o .mdb), valida cada um, confere o hash no manifesto e grava participações,
percursos, parciais e ocorrências com o ritmo já calculado. Ver a spec analise-desempenho (Camada C).
"""
import argparse
import glob
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.analises.parciais import calcularRitmosPorTrecho  # noqa: E402
from src.analises.ritmo import calcularRitmos, formatarRitmo  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosHelga,
    validarDadosParciais,
    validarDadosPercursos,
)

CAMINHO_PADRAO = os.path.join(RAIZ, "Dados", "analise", "analiseCCO.sqlite")

AVISO_INFORMATIVO = (
    "Análise informativa, fora da apuração do campeonato: nada aqui altera pontuação, descarte, desempate ou clubes."
)

ESQUEMA = """
CREATE TABLE metadado (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE fonte (ano INTEGER NOT NULL, arquivo TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY (ano, arquivo));
CREATE TABLE etapa (
    ano INTEGER NOT NULL, numeroEtapa INTEGER NOT NULL, competitionId INTEGER NOT NULL,
    data TEXT, local TEXT, clubeOrganizadorSigla TEXT,
    PRIMARY KEY (ano, numeroEtapa)
);
CREATE TABLE percurso (
    ano INTEGER NOT NULL, competitionId INTEGER NOT NULL, percursoId INTEGER NOT NULL, numero INTEGER NOT NULL,
    distanciaM INTEGER, subidaM INTEGER,
    PRIMARY KEY (ano, percursoId)
);
CREATE TABLE participacao (
    ano INTEGER NOT NULL, numeroEtapa INTEGER NOT NULL, competitionId INTEGER NOT NULL, runnerPk INTEGER NOT NULL,
    cbo INTEGER NOT NULL, nome TEXT NOT NULL, clubeSigla TEXT NOT NULL, categoria TEXT NOT NULL,
    statusCodigo INTEGER NOT NULL, statusSigla TEXT NOT NULL, tempoSegundos INTEGER,
    percursoId INTEGER, distanciaM INTEGER, ritmoSegundosPorKm INTEGER, ritmoTexto TEXT, motivoSemRitmo TEXT,
    PRIMARY KEY (ano, competitionId, runnerPk)
);
CREATE TABLE parcial (
    ano INTEGER NOT NULL, competitionId INTEGER NOT NULL, runnerPk INTEGER NOT NULL, ordem INTEGER NOT NULL,
    codigoPosto INTEGER NOT NULL, distanciaM INTEGER, tempoParcialSegundos INTEGER NOT NULL,
    ritmoSegundosPorKm INTEGER, ritmoTexto TEXT, postosConferem INTEGER NOT NULL,
    PRIMARY KEY (ano, competitionId, runnerPk, ordem)
);
CREATE TABLE ocorrenciaParcial (
    ano INTEGER NOT NULL, competitionId INTEGER NOT NULL, runnerPk INTEGER NOT NULL, motivo TEXT NOT NULL
);
CREATE VIEW vwRitmo AS
    SELECT p.ano, p.numeroEtapa, e.data, e.local, p.categoria, p.nome, p.cbo, p.clubeSigla, p.percursoId,
           p.distanciaM, p.tempoSegundos, p.ritmoSegundosPorKm, p.ritmoTexto
    FROM participacao p JOIN etapa e ON e.ano = p.ano AND e.numeroEtapa = p.numeroEtapa
    WHERE p.ritmoSegundosPorKm IS NOT NULL;
CREATE VIEW vwRitmoTrecho AS
    SELECT t.ano, p.numeroEtapa, p.categoria, p.nome, p.cbo, t.ordem, t.codigoPosto, t.distanciaM,
           t.tempoParcialSegundos, t.ritmoSegundosPorKm, t.ritmoTexto
    FROM parcial t JOIN participacao p ON p.ano = t.ano AND p.competitionId = t.competitionId
         AND p.runnerPk = t.runnerPk
    WHERE t.ritmoSegundosPorKm IS NOT NULL;
"""


@dataclass
class DadosAno:
    """Fontes já validadas de um ano. `percursos` e `parciais` ficam vazios quando o ano não os tem."""

    ano: int
    etapas: dict[str, Any]
    percursos: dict[str, Any] = field(default_factory=lambda: {"percursos": [], "participacoes": []})
    parciais: dict[str, Any] = field(default_factory=lambda: {"percursos": [], "participacoes": [], "ocorrencias": []})
    fontes: list[tuple[str, str]] = field(default_factory=list)


def _lerJson(caminho: str) -> dict[str, Any]:
    with open(caminho, encoding="utf-8") as fh:
        dados: dict[str, Any] = json.load(fh)
    return dados


def etapasApenasDoBanco(dados: dict[str, Any], numerosSubstituidos: set[int]) -> dict[str, Any]:
    """Tira as etapas apuradas por planilha do site (e seus registros): o banco as traz sem resultados reais."""
    return {
        **dados,
        "etapas": [e for e in dados["etapas"] if e["numeroEtapa"] not in numerosSubstituidos],
        "registrosEtapas": [r for r in dados["registrosEtapas"] if r["etapa"] not in numerosSubstituidos],
    }


def carregarAno(ano: int, pastaDados: str) -> DadosAno:
    """Lê, valida e confere no manifesto os JSON do ano; levanta `EntradaInvalidaError`/`OSError` se recusar."""
    pasta = os.path.join(pastaDados, str(ano), "extraidos")
    fontes: list[tuple[str, str]] = []

    def ler(nome: str, validar: Any) -> dict[str, Any]:
        dados = _lerJson(os.path.join(pasta, nome))
        validar(dados)
        conferirHashNoManifesto(dados, ano, pastaDados)
        fontes.append((nome, dados["sha256Fonte"]))
        return dados

    etapas = ler(f"etapasHelga{ano}.json", validarDadosHelga)
    substituidas: set[int] = set()
    for caminho in sorted(glob.glob(os.path.join(pasta, f"etapasHelgaWeb{ano}*.json"))):
        complemento = ler(os.path.basename(caminho), validarDadosHelga)
        substituidas |= {e["numeroEtapa"] for e in complemento["etapas"]}

    resultado = DadosAno(ano=ano, etapas=etapasApenasDoBanco(etapas, substituidas))
    if os.path.isfile(os.path.join(pasta, f"percursosHelga{ano}.json")):
        resultado.percursos = ler(f"percursosHelga{ano}.json", validarDadosPercursos)
    if os.path.isfile(os.path.join(pasta, f"parciaisHelga{ano}.json")):
        resultado.parciais = ler(f"parciaisHelga{ano}.json", validarDadosParciais)
    resultado.fontes = sorted(set(fontes))
    return resultado


def _textoRitmo(segundos: int | None) -> str | None:
    return formatarRitmo(segundos) if segundos is not None else None


def _gravarAno(conn: sqlite3.Connection, dados: DadosAno) -> None:
    ano = dados.ano
    conn.executemany(
        "INSERT INTO fonte (ano, arquivo, sha256) VALUES (?, ?, ?)", [(ano, a, h) for a, h in dados.fontes],
    )
    conn.executemany(
        "INSERT INTO etapa (ano, numeroEtapa, competitionId, data, local, clubeOrganizadorSigla) VALUES (?, ?, ?, ?, ?, ?)",
        [(ano, e["numeroEtapa"], e["competitionId"], e.get("data"), e.get("local"), e.get("clubeOrganizadorSigla"))
         for e in sorted(dados.etapas["etapas"], key=lambda e: e["numeroEtapa"])],
    )
    conn.executemany(
        "INSERT INTO percurso (ano, competitionId, percursoId, numero, distanciaM, subidaM) VALUES (?, ?, ?, ?, ?, ?)",
        [(ano, p["competitionId"], p["percursoId"], p["numero"], p["distanciaM"], p["subidaM"])
         for p in sorted(dados.percursos["percursos"], key=lambda p: p["percursoId"])],
    )

    ritmos, semRitmo = calcularRitmos(dados.etapas, dados.percursos)
    ritmoPor = {(r.etapa, r.cbo, r.categoria): r for r in ritmos}
    motivoPor = {(s.etapa, s.cbo, s.categoria): s.motivo for s in semRitmo}
    percursoPor = {
        (p["competitionId"], p["runnerPk"]): p["percursoId"] for p in dados.percursos["participacoes"]
    }
    distanciaPor = {p["percursoId"]: p["distanciaM"] for p in dados.percursos["percursos"]}
    linhas = []
    for r in sorted(dados.etapas["registrosEtapas"], key=lambda r: (r["etapa"], r["competitionId"], r["runnerPk"])):
        chave = (r["etapa"], r["cbo"], r["categoria"])
        ritmo = ritmoPor.get(chave)
        percursoId = percursoPor.get((r["competitionId"], r["runnerPk"]))
        linhas.append((
            ano, r["etapa"], r["competitionId"], r["runnerPk"], r["cbo"], r["nome"], r["clubeSigla"], r["categoria"],
            r["statusCodigo"], r["statusSigla"], r["tempoSegundos"], percursoId,
            distanciaPor.get(percursoId) if percursoId is not None else None,
            ritmo.ritmoSegundosPorKm if ritmo else None, _textoRitmo(ritmo.ritmoSegundosPorKm) if ritmo else None,
            None if ritmo else motivoPor.get(chave),
        ))
    conn.executemany(
        "INSERT INTO participacao (ano, numeroEtapa, competitionId, runnerPk, cbo, nome, clubeSigla, categoria, "
        "statusCodigo, statusSigla, tempoSegundos, percursoId, distanciaM, ritmoSegundosPorKm, ritmoTexto, "
        "motivoSemRitmo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        linhas,
    )

    trechos, _ = calcularRitmosPorTrecho(dados.parciais)
    trechoPor = {(t.competitionId, t.runnerPk, t.ordem): t for t in trechos}
    postos = {
        (p["percursoId"], posto["ordem"]): posto["distanciaM"] for p in dados.parciais["percursos"]
        for posto in p["postos"]
    }
    parciais = []
    for p in sorted(dados.parciais["participacoes"], key=lambda p: (p["competitionId"], p["runnerPk"])):
        for passagem in p["passagens"]:
            trecho = trechoPor.get((p["competitionId"], p["runnerPk"], passagem["ordem"]))
            parciais.append((
                ano, p["competitionId"], p["runnerPk"], passagem["ordem"], passagem["codigoPosto"],
                postos.get((p["percursoId"], passagem["ordem"])) if p["postosConferem"] else None,
                passagem["tempoParcialSegundos"], trecho.ritmoSegundosPorKm if trecho else None,
                _textoRitmo(trecho.ritmoSegundosPorKm) if trecho else None, int(p["postosConferem"]),
            ))
    conn.executemany(
        "INSERT INTO parcial (ano, competitionId, runnerPk, ordem, codigoPosto, distanciaM, tempoParcialSegundos, "
        "ritmoSegundosPorKm, ritmoTexto, postosConferem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        parciais,
    )
    conn.executemany(
        "INSERT INTO ocorrenciaParcial (ano, competitionId, runnerPk, motivo) VALUES (?, ?, ?, ?)",
        [(ano, o["competitionId"], o["runnerPk"], o["motivo"]) for o in dados.parciais["ocorrencias"]],
    )


def construirBase(caminhoSaida: str, anos: list[DadosAno]) -> None:
    """Grava a base em `caminhoSaida`, substituindo a anterior. Sem datas de geração: a saída é reproduzível."""
    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaida)), exist_ok=True)
    temporario = f"{caminhoSaida}.tmp"
    if os.path.exists(temporario):
        os.remove(temporario)
    conn = sqlite3.connect(temporario)
    try:
        conn.executescript(ESQUEMA)
        conn.executemany("INSERT INTO metadado (chave, valor) VALUES (?, ?)", [
            ("aviso", AVISO_INFORMATIVO),
            ("anos", ",".join(str(d.ano) for d in sorted(anos, key=lambda d: d.ano))),
            ("dicionario", ".agents/wiki/dicionario-dados-analise.md"),
        ])
        for dados in sorted(anos, key=lambda d: d.ano):
            _gravarAno(conn, dados)
        conn.commit()
    except BaseException:
        conn.close()
        os.remove(temporario)
        raise
    conn.close()
    os.replace(temporario, caminhoSaida)


def anosDisponiveis(pastaDados: str) -> list[int]:
    """Anos com `etapasHelga<ano>.json` em Dados/<ano>/extraidos/."""
    return sorted(
        int(nome) for nome in os.listdir(pastaDados)
        if nome.isdigit() and os.path.isfile(os.path.join(pastaDados, nome, "extraidos", f"etapasHelga{nome}.json"))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera a base SQLite de análise de desempenho (ADR-009).")
    parser.add_argument("--saida", default=CAMINHO_PADRAO, help="Caminho da base SQLite de saída")
    parser.add_argument("--ano", type=int, action="append", default=None, help="Só este ano (pode repetir)")
    args = parser.parse_args()

    pastaDados = os.path.join(RAIZ, "Dados")
    anos = args.ano or anosDisponiveis(pastaDados)
    try:
        carregados = [carregarAno(ano, pastaDados) for ano in anos]
    except (OSError, EntradaInvalidaError) as erro:
        print(f"Entrada recusada: {erro}", file=sys.stderr)
        return 1
    if not carregados:
        print("Nenhum ano com etapasHelga<ano>.json em Dados/<ano>/extraidos/.", file=sys.stderr)
        return 1

    construirBase(args.saida, carregados)
    print(f"Base gerada: {args.saida} (anos {', '.join(str(d.ano) for d in carregados)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
