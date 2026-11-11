# -*- coding: utf-8 -*-
"""Carrega os dados extraídos de um ano: JSON do banco mais os complementos (planilha do site do Helga).

As etapas de um complemento substituem as de mesmo número do JSON do banco (spec web-results-ingestion e
ADR-006). Cada arquivo é validado e tem o hash conferido no manifesto antes de ser mesclado.
"""
import glob
import json
import os
from typing import Any

from src.extracaoAccess.validarEntrada import conferirHashNoManifesto, validarDadosHelga


def mesclarComplemento(base: dict[str, Any], complemento: dict[str, Any]) -> dict[str, Any]:
    """Mescla um complemento ao JSON-base; as etapas do complemento substituem as de mesmo número."""
    substituidas = {e["numeroEtapa"] for e in complemento["etapas"]}
    clubes = {c["clubeId"]: c for c in complemento["clubes"]}
    clubes.update({c["clubeId"]: c for c in base["clubes"]})   # na divergência vale o cadastro do banco
    return {
        "fonte": base["fonte"],
        "sha256Fonte": base["sha256Fonte"],
        "etapas": sorted(
            [e for e in base["etapas"] if e["numeroEtapa"] not in substituidas] + complemento["etapas"],
            key=lambda e: e["numeroEtapa"],
        ),
        "clubes": list(clubes.values()),
        "perfisAtletas": {**complemento["perfisAtletas"], **base["perfisAtletas"]},
        "registrosEtapas": (
            [r for r in base["registrosEtapas"] if r["etapa"] not in substituidas] + complemento["registrosEtapas"]
        ),
    }


def carregarDadosDoAno(ano: int, pastaDados: str) -> tuple[dict[str, Any], list[str]]:
    """Lê, valida e mescla os extraídos do ano; devolve os dados e os nomes dos arquivos usados.

    Levanta `ValueError`/`OSError` (inclusive `EntradaInvalidaError`) se algum arquivo for recusado.
    """
    pastaExtraidos = os.path.join(pastaDados, str(ano), "extraidos")
    caminhoBase = os.path.join(pastaExtraidos, f"etapasHelga{ano}.json")
    complementos = sorted(glob.glob(os.path.join(pastaExtraidos, f"etapasHelgaWeb{ano}*.json")))
    usados: list[str] = []
    dados: dict[str, Any] = {}
    for caminho in [caminhoBase, *complementos]:
        with open(caminho, encoding="utf-8") as fh:
            parcial = json.load(fh)
        validarDadosHelga(parcial)
        conferirHashNoManifesto(parcial, ano, pastaDados)
        dados = parcial if not dados else mesclarComplemento(dados, parcial)
        usados.append(os.path.basename(caminho))
    return dados, usados
