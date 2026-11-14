# -*- coding: utf-8 -*-
"""Ritmo médio de cada participação (spec analise-desempenho, Camada A).

Funções puras: não acessam banco nem sistema de arquivos. O ritmo é informativo, nunca entra na pontuação,
no descarte nem no desempate, e só se compara dentro da mesma categoria ou do mesmo percurso.
"""
from dataclasses import dataclass
from typing import Any

STATUS_CONCLUIU = 0


@dataclass(frozen=True)
class RitmoAtleta:
    """Ritmo de uma participação que concluiu o percurso, com a distância usada no cálculo."""

    etapa: int
    cbo: int
    nome: str
    categoria: str
    percursoId: int
    distanciaM: int
    tempoSegundos: int
    ritmoSegundosPorKm: int


@dataclass(frozen=True)
class SemRitmo:
    """Participação sem ritmo e o motivo."""

    etapa: int
    cbo: int
    nome: str
    categoria: str
    motivo: str


def calcularRitmoSegundosPorKm(tempoSegundos: int, distanciaM: int) -> int:
    """Ritmo em segundos por quilômetro, arredondado ao segundo com a metade para cima.

    A metade sobe (convenção do projeto): 3806 s em 4000 m são 951,5 s/km e valem 952 s, ou 15'52".
    Aritmética inteira: evita o erro do ponto flutuante e o arredondamento da metade ao par do Python.

    Em empate exato de meio segundo o site do HelgaO ora sobe, ora desce, e o resultado pode diferir 1 s do
    daqui; a causa provável (não verificada) é o Helga calcular com milissegundos, que o banco não traz
    (`CourseTime_ms` vem zerado). Fora dos empates, o ritmo coincide com o do site (spec analise-desempenho).
    """
    if tempoSegundos <= 0:
        raise ValueError(f"tempo deve ser positivo: {tempoSegundos}")
    if distanciaM <= 0:
        raise ValueError(f"distância deve ser positiva: {distanciaM}")
    return (2 * tempoSegundos * 1000 + distanciaM) // (2 * distanciaM)


def formatarRitmo(ritmoSegundosPorKm: int) -> str:
    """Formata o ritmo como `m'ss"` (minutos e segundos por quilômetro)."""
    minutos, segundos = divmod(ritmoSegundosPorKm, 60)
    return f"{minutos}'{segundos:02d}\""


def calcularRitmos(
    dadosEtapas: dict[str, Any], dadosPercursos: dict[str, Any],
) -> tuple[list[RitmoAtleta], list[SemRitmo]]:
    """Calcula o ritmo de cada participação, ligando `registrosEtapas` e `participacoes` por competição e atleta.

    Só quem concluiu (`statusCodigo` 0) com tempo e percurso com distância recebe ritmo; os demais voltam em
    `SemRitmo` com o motivo. Entradas já validadas por `validarDadosHelga` e `validarDadosPercursos`.
    """
    distanciaPorPercurso = {p["percursoId"]: p["distanciaM"] for p in dadosPercursos["percursos"]}
    percursoPorParticipacao = {
        (p["competitionId"], p["runnerPk"]): p["percursoId"] for p in dadosPercursos["participacoes"]
    }

    ritmos: list[RitmoAtleta] = []
    semRitmo: list[SemRitmo] = []
    for r in dadosEtapas["registrosEtapas"]:
        base = (r["etapa"], r["cbo"], r["nome"], r["categoria"])
        if r["statusCodigo"] != STATUS_CONCLUIU:
            semRitmo.append(SemRitmo(*base, f"não concluiu ({r['statusSigla']})"))
            continue
        if not r["tempoSegundos"]:
            semRitmo.append(SemRitmo(*base, "sem tempo"))
            continue
        percursoId = percursoPorParticipacao.get((r["competitionId"], r["runnerPk"]))
        if percursoId is None:
            semRitmo.append(SemRitmo(*base, "sem percurso"))
            continue
        distanciaM = distanciaPorPercurso.get(percursoId)
        if not distanciaM:
            semRitmo.append(SemRitmo(*base, "percurso sem distância"))
            continue
        ritmos.append(RitmoAtleta(
            etapa=r["etapa"], cbo=r["cbo"], nome=r["nome"], categoria=r["categoria"], percursoId=percursoId,
            distanciaM=distanciaM, tempoSegundos=r["tempoSegundos"],
            ritmoSegundosPorKm=calcularRitmoSegundosPorKm(r["tempoSegundos"], distanciaM),
        ))
    return ritmos, semRitmo
