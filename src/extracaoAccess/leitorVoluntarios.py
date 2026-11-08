# -*- coding: utf-8 -*-
"""Leitor do arquivo Markdown de voluntários e penalidades (Art. 33 e Art. 23 do Regulamento)."""
import re
from typing import Any


def lerVoluntariosMarkdown(textoMd: str) -> dict[str, Any]:
    """Lê as tabelas Markdown de voluntários/convocados, penalidades do Art. 23 e unificações de CBO.

    Espera tabelas com colunas `| Etapa | CBO | Voluntário / Convocado |` (ex.: `1ª | 10641 | Nome`)
    ou `| CBO Provisório | CBO Oficial | Atleta | Clube Oficial |` na seção de unificação.
    """
    voluntarios: list[dict[str, Any]] = []
    arbitros: list[dict[str, Any]] = []
    penalidadesArt23: list[dict[str, Any]] = []
    unificacoesCbo: list[dict[str, Any]] = []
    secaoAtual = "voluntarios"

    for linha in textoMd.splitlines():
        linhaLimpa = linha.strip()
        if linhaLimpa.startswith("## "):
            titulo = linhaLimpa[3:].strip().lower()
            if "penalidade" in titulo or "art. 23" in titulo:
                secaoAtual = "penalidades"
            elif "árbitro" in titulo or "arbitro" in titulo:
                secaoAtual = "arbitros"
            elif "unificação" in titulo or "unificacao" in titulo:
                secaoAtual = "unificacoes"
            else:
                secaoAtual = "voluntarios"
            continue

        if not linhaLimpa.startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|?$", linhaLimpa):
            continue

        celulas = [c.strip() for c in linhaLimpa.strip("|").split("|")]
        if len(celulas) < 3:
            continue
        primeiraColuna = celulas[0].lower()
        if primeiraColuna in ("etapa", "percurso") or primeiraColuna.startswith("cbo"):
            continue

        if secaoAtual == "unificacoes":
            mProv = re.search(r"(\d+)", celulas[0])
            mOfic = re.search(r"(\d+)", celulas[1])
            if not mProv or not mOfic:
                continue
            itemUnif: dict[str, Any] = {
                "cboProvisorio": int(mProv.group(1)),
                "cboOficial": int(mOfic.group(1)),
                "nome": celulas[2],
            }
            if len(celulas) >= 4 and celulas[3]:
                itemUnif["clubeSigla"] = celulas[3]
            unificacoesCbo.append(itemUnif)
            continue

        mEtapa = re.search(r"(\d+)", celulas[0])
        mCbo = re.search(r"(\d+)", celulas[1])
        if not mEtapa or not mCbo:
            continue

        registro: dict[str, Any] = {
            "etapa": int(mEtapa.group(1)),
            "cbo": int(mCbo.group(1)),
            "nome": celulas[2],
            "funcao": "arbitro" if secaoAtual == "arbitros" else "voluntario",
        }
        if secaoAtual == "arbitros" and len(celulas) >= 4:
            mQa = re.search(r"(\d+)", celulas[3])
            if mQa:
                registro["qaFecori"] = int(mQa.group(1))

        if secaoAtual == "penalidades":
            penalidadesArt23.append(registro)
        else:
            voluntarios.append(registro)
            if secaoAtual == "arbitros":
                arbitros.append(registro)

    return {
        "voluntarios": voluntarios,
        "arbitros": arbitros,
        "penalidadesArt23": penalidadesArt23,
        "unificacoesCbo": unificacoesCbo,
    }

