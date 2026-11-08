#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utilitário para inspecionar o esquema (tabelas e colunas) de um arquivo .mdb/.accdb
e calcular seu hash SHA-256 para o manifesto de arquivos congelados.
"""
import argparse
import hashlib
import os
import sys


def calcularSha256(caminhoArquivo: str) -> str:
    """Calcula o hash SHA-256 de um arquivo em disco."""
    hasher = hashlib.sha256()
    with open(caminhoArquivo, 'rb') as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b''):
            hasher.update(bloco)
    return hasher.hexdigest()


def inspecionarEsquemaAccess(caminhoArquivo: str) -> dict[str, list[tuple[str, str]]]:
    """Lista tabelas e colunas de um arquivo .mdb ou .accdb via pyodbc (sem ler dados pessoais)."""
    try:
        import pyodbc  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "A biblioteca 'pyodbc' não está instalada. Instale com: pip install pyodbc"
        ) from exc

    caminhoAbsoluto = os.path.abspath(caminhoArquivo)
    connStr = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={caminhoAbsoluto};ReadOnly=1;"
    )
    esquema: dict[str, list[tuple[str, str]]] = {}
    with pyodbc.connect(connStr) as conexao:
        cursor = conexao.cursor()
        tabelas = [
            row.table_name
            for row in cursor.tables(tableType='TABLE')
            if not row.table_name.startswith('MSys')
        ]
        for tabela in sorted(tabelas):
            colunas = [
                (col.column_name, col.type_name)
                for col in cursor.columns(table=tabela)
            ]
            esquema[tabela] = colunas
    return esquema


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspeciona tabelas/colunas de banco Microsoft Access (.mdb/.accdb) e exibe seu SHA-256."
    )
    parser.add_argument('--arquivo', required=True, help="Caminho para o arquivo .mdb ou .accdb")
    args = parser.parse_args()

    if not os.path.isfile(args.arquivo):
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 1

    sha256 = calcularSha256(args.arquivo)
    print(f"SHA-256: {sha256}  {os.path.basename(args.arquivo)}\n")

    try:
        esquema = inspecionarEsquemaAccess(args.arquivo)
    except Exception as erro:
        print(f"Aviso ao abrir via ODBC: {erro}", file=sys.stderr)
        return 1

    print(f"Tabelas encontradas ({len(esquema)}):")
    for tabela, colunas in esquema.items():
        nomesColunas = ", ".join(f"{nome} ({tipo})" for nome, tipo in colunas)
        print(f"  - {tabela}: {nomesColunas}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

