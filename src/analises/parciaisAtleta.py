#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mostra as parciais e o ritmo por trecho de um atleta numa etapa (informativo, fora da apuração).

Lê os JSON higienizados de Dados/<ano>/extraidos/ (nunca o .mdb) e confere o hash de cada um no manifesto.
Ver a spec analise-desempenho.
"""
import argparse
import json
import os
import sys
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.analises.parciais import calcularRitmosPorTrecho  # noqa: E402
from src.analises.ritmo import formatarRitmo  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosHelga,
    validarDadosParciais,
)


def _lerJson(caminho: str) -> dict[str, Any]:
    with open(caminho, encoding="utf-8") as fh:
        dados: dict[str, Any] = json.load(fh)
    return dados


def _mmss(segundos: int) -> str:
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas}:{minutos:02d}:{seg:02d}" if horas else f"{minutos:02d}:{seg:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Parciais e ritmo por trecho de um atleta (informativo).")
    parser.add_argument("--ano", type=int, default=2026, help="Ano da edição")
    parser.add_argument("--etapa", type=int, required=True, help="Número da etapa")
    parser.add_argument("--cbo", type=int, required=True, help="Número CBO do atleta")
    args = parser.parse_args()

    pastaDados = os.path.join(RAIZ, "Dados")
    pastaExtraidos = os.path.join(pastaDados, str(args.ano), "extraidos")
    try:
        dadosEtapas = _lerJson(os.path.join(pastaExtraidos, f"etapasHelga{args.ano}.json"))
        dadosParciais = _lerJson(os.path.join(pastaExtraidos, f"parciaisHelga{args.ano}.json"))
        validarDadosHelga(dadosEtapas)
        validarDadosParciais(dadosParciais)
        conferirHashNoManifesto(dadosEtapas, args.ano, pastaDados)
        conferirHashNoManifesto(dadosParciais, args.ano, pastaDados)
    except (OSError, EntradaInvalidaError) as erro:
        print(f"Entrada recusada: {erro}", file=sys.stderr)
        return 1

    registro = next(
        (r for r in dadosEtapas["registrosEtapas"] if r["etapa"] == args.etapa and r["cbo"] == args.cbo), None,
    )
    if registro is None:
        print(f"Atleta {args.cbo} sem inscrição na etapa {args.etapa}.", file=sys.stderr)
        return 1
    chave = (registro["competitionId"], registro["runnerPk"])

    ocorrencias = [
        o["motivo"] for o in dadosParciais["ocorrencias"] if (o["competitionId"], o["runnerPk"]) == chave
    ]
    participacao = next(
        (p for p in dadosParciais["participacoes"] if (p["competitionId"], p["runnerPk"]) == chave), None,
    )
    print(f"{registro['nome']} | etapa {args.etapa} | {registro['categoria']} (informativo, fora da apuração)")
    for motivo in ocorrencias:
        print(f"Ocorrência: {motivo}")
    if participacao is None:
        print("Sem parciais aceitas para esta participação.")
        return 0

    ritmos, _ = calcularRitmosPorTrecho(dadosParciais)
    ritmoPorOrdem = {r.ordem: r for r in ritmos if (r.competitionId, r.runnerPk) == chave}
    print("trecho | posto | distância | parcial | ritmo")
    for passagem in participacao["passagens"]:
        r = ritmoPorOrdem.get(passagem["ordem"])
        distancia = f"{r.distanciaM} m" if r else "-"
        ritmo = f"{formatarRitmo(r.ritmoSegundosPorKm)}/km" if r else "-"
        print(f"{passagem['ordem']} | {passagem['codigoPosto']} | {distancia} | "
              f"{_mmss(passagem['tempoParcialSegundos'])} | {ritmo}")
    print(f"Tempo oficial: {_mmss(participacao['tempoOficialSegundos'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
