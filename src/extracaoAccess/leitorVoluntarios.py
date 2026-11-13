# -*- coding: utf-8 -*-
"""Leitor do arquivo Markdown de voluntários e penalidades (Art. 33 e Art. 23 do Regulamento)."""
import re
from typing import Any

# Número isolado de até 9 dígitos: evita converter sequências enormes e ignora texto colado (ex.: "1ª").
_NUMERO = re.compile(r"(?<!\d)(\d{1,9})(?!\d)")


def lerVoluntariosMarkdown(textoMd: str) -> dict[str, Any]:
    """Lê as tabelas Markdown de voluntários/convocados, penalidades do Art. 23, unificações de CBO e ajustes oficiais.

    Espera tabelas com colunas `| Etapa | CBO | Voluntário / Convocado |` (ex.: `1ª | 10641 | Nome`)
    ou `| CBO Provisório | CBO Oficial | Atleta | Clube Oficial |` na seção de unificação.
    """
    voluntarios: list[dict[str, Any]] = []
    arbitros: list[dict[str, Any]] = []
    penalidadesArt23: list[dict[str, Any]] = []
    unificacoesCbo: list[dict[str, Any]] = []
    ajustesOficiais: list[dict[str, Any]] = []
    posicoesOficiais: list[dict[str, Any]] = []
    omissoesOficiais: list[dict[str, Any]] = []
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
            elif "fora do resultado" in titulo:
                secaoAtual = "omissoes"
            elif "ajuste" in titulo:
                secaoAtual = "ajustes"
            elif "posições" in titulo or "posicoes" in titulo:
                secaoAtual = "posicoes"
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

        if secaoAtual == "omissoes":
            # | Categoria | CBO | Motivo |
            mCboOm = re.search(_NUMERO, celulas[1])
            if not mCboOm:
                continue
            omissoesOficiais.append({
                "categoria": celulas[0],
                "cbo": int(mCboOm.group(1)),
                "motivo": celulas[2],
            })
            continue

        if secaoAtual == "posicoes":
            # | Categoria | CBO | Posição publicada | Motivo |
            mCboPos = re.search(_NUMERO, celulas[1])
            mPos = re.search(_NUMERO, celulas[2])
            if not mCboPos or not mPos:
                continue
            posicoesOficiais.append({
                "categoria": celulas[0],
                "cbo": int(mCboPos.group(1)),
                "posicao": int(mPos.group(1)),
                "motivo": celulas[3] if len(celulas) >= 4 else "",
            })
            continue

        if secaoAtual == "ajustes":
            # | Etapa | CBO | Categoria | Pontos publicados | Motivo | Destaque |  (pontos e destaque validados pelo motor)
            mEtapaAj = re.search(_NUMERO, celulas[0])
            mCboAj = re.search(_NUMERO, celulas[1])
            if not mEtapaAj or not mCboAj or len(celulas) < 4:
                continue
            ajustesOficiais.append({
                "etapa": int(mEtapaAj.group(1)),
                "cbo": int(mCboAj.group(1)),
                "categoria": celulas[2],
                "pontos": celulas[3],
                "motivo": celulas[4] if len(celulas) >= 5 else "",
                "destaque": celulas[5].strip().lower() if len(celulas) >= 6 else "",
            })
            continue

        if secaoAtual == "unificacoes":
            mProv = re.search(_NUMERO, celulas[0])
            mOfic = re.search(_NUMERO, celulas[1])
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

        mEtapa = re.search(_NUMERO, celulas[0])
        mCbo = re.search(_NUMERO, celulas[1])
        if not mEtapa or not mCbo:
            continue

        registro: dict[str, Any] = {
            "etapa": int(mEtapa.group(1)),
            "cbo": int(mCbo.group(1)),
            "nome": celulas[2],
            "funcao": "arbitro" if secaoAtual == "arbitros" else "voluntario",
        }
        if secaoAtual == "arbitros" and len(celulas) >= 4:
            mQa = re.search(_NUMERO, celulas[3])
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
        "ajustesOficiais": ajustesOficiais,
        "posicoesOficiais": posicoesOficiais,
        "omissoesOficiais": omissoesOficiais,
    }

