#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lista o ritmo médio de cada participação de uma edição (informativo, fora da apuração).

Lê os JSON higienizados de Dados/<ano>/extraidos/ (nunca o .mdb), confere o hash de cada um no manifesto e
imprime o ritmo por etapa e categoria. Ver a spec analise-desempenho.
"""
import argparse
import json
import os
import sys
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.analises.ritmo import RitmoAtleta, calcularRitmos, formatarRitmo  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosHelga,
    validarDadosPercursos,
)


def _lerJson(caminho: str) -> dict[str, Any]:
    with open(caminho, encoding="utf-8") as fh:
        dados: dict[str, Any] = json.load(fh)
    return dados


def _linha(r: RitmoAtleta) -> str:
    return (
        f"{r.etapa} | {r.categoria} | {r.nome} | {r.distanciaM} m | "
        f"{r.tempoSegundos // 3600:02d}:{r.tempoSegundos % 3600 // 60:02d}:{r.tempoSegundos % 60:02d} | "
        f"{formatarRitmo(r.ritmoSegundosPorKm)}/km"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ritmo médio por participação (informativo).")
    parser.add_argument("--ano", type=int, default=2026, help="Ano da edição")
    parser.add_argument("--etapa", type=int, default=None, help="Mostra só esta etapa")
    parser.add_argument("--categoria", default=None, help="Mostra só esta categoria (nome exato)")
    args = parser.parse_args()

    pastaDados = os.path.join(RAIZ, "Dados")
    pastaExtraidos = os.path.join(pastaDados, str(args.ano), "extraidos")
    try:
        dadosEtapas = _lerJson(os.path.join(pastaExtraidos, f"etapasHelga{args.ano}.json"))
        dadosPercursos = _lerJson(os.path.join(pastaExtraidos, f"percursosHelga{args.ano}.json"))
        validarDadosHelga(dadosEtapas)
        validarDadosPercursos(dadosPercursos)
        conferirHashNoManifesto(dadosEtapas, args.ano, pastaDados)
        conferirHashNoManifesto(dadosPercursos, args.ano, pastaDados)
    except (OSError, EntradaInvalidaError) as erro:
        print(f"Entrada recusada: {erro}", file=sys.stderr)
        return 1

    ritmos, semRitmo = calcularRitmos(dadosEtapas, dadosPercursos)
    selecionados = sorted(
        (r for r in ritmos
         if (args.etapa is None or r.etapa == args.etapa) and (args.categoria is None or r.categoria == args.categoria)),
        key=lambda r: (r.etapa, r.categoria, r.ritmoSegundosPorKm, r.nome),
    )

    print("Ritmo informativo, fora da apuração. Distância: Parcours.Length do Helga, em metros.")
    print("etapa | categoria | atleta | distância | tempo | ritmo")
    for r in selecionados:
        print(_linha(r))
    print(f"{len(selecionados)} participações com ritmo; {len(semRitmo)} sem ritmo na edição inteira.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
