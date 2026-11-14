#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Consulta SQL somente leitura à base SQLite de análise de desempenho (ADR-009).

Abre a base com `mode=ro`, aceita um único `SELECT` (ou `WITH ... SELECT`), recusa qualquer outra operação por
meio do autorizador do SQLite, limita as linhas devolvidas e interrompe consultas longas demais. A IA escreve o
SQL e roda este script; a conta (média, mediana, ritmo) é feita pelo SQL.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAMINHO_PADRAO = os.path.join(RAIZ, "Dados", "analise", "analiseCCO.sqlite")
LIMITE_PADRAO = 200
LIMITE_MAXIMO = 5000
# Cada chamada do manipulador de progresso corresponde a 1.000 instruções da máquina virtual do SQLite.
INSTRUCOES_POR_CHAMADA = 1000
CHAMADAS_MAXIMAS = 100_000

_COMECA_COM_CONSULTA = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_ACOES_PERMITIDAS = frozenset({
    sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE,
})


class ConsultaRecusadaError(ValueError):
    """Consulta recusada: não é uma leitura simples da base."""


def _autorizar(acao: int, arg1: str | None, arg2: str | None, banco: str | None, origem: str | None) -> int:
    """Autorizador do SQLite: só leitura (SELECT, colunas e funções), nada de escrita, PRAGMA ou ATTACH."""
    return sqlite3.SQLITE_OK if acao in _ACOES_PERMITIDAS else sqlite3.SQLITE_DENY


def normalizarConsulta(sql: str) -> str:
    """Exige um único `SELECT`/`WITH` e remove o `;` final; levanta `ConsultaRecusadaError` caso contrário."""
    consulta = sql.strip().rstrip(";").strip()
    if not consulta:
        raise ConsultaRecusadaError("consulta vazia")
    if not _COMECA_COM_CONSULTA.match(consulta):
        raise ConsultaRecusadaError("só são aceitas consultas que começam com SELECT ou WITH")
    return consulta


def abrirSomenteLeitura(caminhoBase: str) -> sqlite3.Connection:
    """Abre a base em modo somente leitura, com autorizador e limite de instruções."""
    if not os.path.isfile(caminhoBase):
        raise FileNotFoundError(f"base não encontrada: {caminhoBase} (gere com python src/analises/gerarBase.py)")
    conn = sqlite3.connect(f"{Path(caminhoBase).resolve().as_uri()}?mode=ro", uri=True)
    chamadas = 0

    def _limitar() -> int:
        nonlocal chamadas
        chamadas += 1
        return 1 if chamadas > CHAMADAS_MAXIMAS else 0

    conn.set_authorizer(_autorizar)
    conn.set_progress_handler(_limitar, INSTRUCOES_POR_CHAMADA)
    return conn


def consultar(caminhoBase: str, sql: str, limite: int = LIMITE_PADRAO) -> tuple[list[str], list[tuple[Any, ...]], bool]:
    """Executa a consulta e devolve (colunas, linhas, truncado). Levanta `ConsultaRecusadaError` ou `sqlite3.Error`."""
    if not 1 <= limite <= LIMITE_MAXIMO:
        raise ConsultaRecusadaError(f"limite deve estar entre 1 e {LIMITE_MAXIMO}")
    consulta = normalizarConsulta(sql)
    conn = abrirSomenteLeitura(caminhoBase)
    try:
        try:
            cursor = conn.execute(consulta)
        except (sqlite3.Warning, sqlite3.ProgrammingError) as erro:   # inclui mais de uma instrução
            raise ConsultaRecusadaError(str(erro)) from erro
        colunas = [d[0] for d in cursor.description or []]
        linhas = cursor.fetchmany(limite + 1)
    finally:
        conn.close()
    return colunas, linhas[:limite], len(linhas) > limite


def _formatarTexto(colunas: list[str], linhas: list[tuple[Any, ...]], truncado: bool, limite: int) -> str:
    saida = [" | ".join(colunas)]
    saida += [" | ".join("" if v is None else str(v) for v in linha) for linha in linhas]
    saida.append(f"({len(linhas)} linha(s){f'; truncado em {limite}, use --limite' if truncado else ''})")
    return "\n".join(saida)


def main() -> int:
    parser = argparse.ArgumentParser(description="Consulta SQL somente leitura à base de análise de desempenho.")
    parser.add_argument("sql", help="Consulta: um único SELECT (ou WITH ... SELECT)")
    parser.add_argument("--base", default=CAMINHO_PADRAO, help="Caminho da base SQLite")
    parser.add_argument("--limite", type=int, default=LIMITE_PADRAO, help=f"Máximo de linhas (até {LIMITE_MAXIMO})")
    parser.add_argument("--json", action="store_true", help="Saída em JSON em vez de texto")
    args = parser.parse_args()

    try:
        colunas, linhas, truncado = consultar(args.base, args.sql, args.limite)
    except (ConsultaRecusadaError, sqlite3.Error, OSError) as erro:
        print(f"Consulta recusada: {erro}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(
            {"colunas": colunas, "linhas": [list(linha) for linha in linhas], "truncado": truncado},
            ensure_ascii=False,
        ))
    else:
        print(_formatarTexto(colunas, linhas, truncado, args.limite))
    return 0


if __name__ == "__main__":
    sys.exit(main())
