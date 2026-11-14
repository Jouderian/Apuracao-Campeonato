# -*- coding: utf-8 -*-
"""Ritmo por trecho de cada participação (spec analise-desempenho, Camada B).

Funções puras sobre o JSON de parciais. O ritmo por trecho é informativo, usa a distância do trecho do Helga
(`Controls.Distance`, que somada fica abaixo da distância do percurso) e só se compara dentro da mesma categoria
ou do mesmo percurso.
"""
from dataclasses import dataclass
from typing import Any

from src.analises.ritmo import calcularRitmoSegundosPorKm


@dataclass(frozen=True)
class RitmoTrecho:
    """Ritmo de um trecho (entre dois postos) de uma participação, com a distância usada."""

    competitionId: int
    runnerPk: int
    ordem: int
    codigoPosto: int
    distanciaM: int
    tempoParcialSegundos: int
    ritmoSegundosPorKm: int


@dataclass(frozen=True)
class SemRitmoTrecho:
    """Participação ou trecho sem ritmo e o motivo (`ordem` vazia quando vale para a participação inteira)."""

    competitionId: int
    runnerPk: int
    ordem: int | None
    motivo: str


def calcularRitmosPorTrecho(dadosParciais: dict[str, Any]) -> tuple[list[RitmoTrecho], list[SemRitmoTrecho]]:
    """Calcula o ritmo de cada trecho das participações cuja sequência de postos confere com a do percurso.

    Participação com `postosConferem` falso fica sem ritmo (a distância do trecho só vale na sequência do
    percurso). Trecho sem distância ou com parcial zero ou negativa também fica sem ritmo, com o motivo.
    Entrada já validada por `validarDadosParciais`.
    """
    distanciaPorTrecho: dict[tuple[int, int], int | None] = {
        (percurso["percursoId"], posto["ordem"]): posto["distanciaM"]
        for percurso in dadosParciais["percursos"]
        for posto in percurso["postos"]
    }

    ritmos: list[RitmoTrecho] = []
    semRitmo: list[SemRitmoTrecho] = []
    for p in dadosParciais["participacoes"]:
        if not p["postosConferem"]:
            semRitmo.append(SemRitmoTrecho(p["competitionId"], p["runnerPk"], None, "sequência de postos difere do percurso"))
            continue
        for passagem in p["passagens"]:
            distanciaM = distanciaPorTrecho.get((p["percursoId"], passagem["ordem"]))
            if not distanciaM:
                semRitmo.append(SemRitmoTrecho(p["competitionId"], p["runnerPk"], passagem["ordem"], "trecho sem distância"))
            elif passagem["tempoParcialSegundos"] <= 0:
                semRitmo.append(SemRitmoTrecho(p["competitionId"], p["runnerPk"], passagem["ordem"], "parcial zero ou negativa"))
            else:
                ritmos.append(RitmoTrecho(
                    competitionId=p["competitionId"], runnerPk=p["runnerPk"], ordem=passagem["ordem"],
                    codigoPosto=passagem["codigoPosto"], distanciaM=distanciaM,
                    tempoParcialSegundos=passagem["tempoParcialSegundos"],
                    ritmoSegundosPorKm=calcularRitmoSegundosPorKm(passagem["tempoParcialSegundos"], distanciaM),
                ))
    return ritmos, semRitmo
