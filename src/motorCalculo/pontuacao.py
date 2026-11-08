# -*- coding: utf-8 -*-
"""Regras puras de pontuação e apuração do Campeonato Cearense de Orientação (CCO e CCOS).

Implementa os dispositivos do Capítulo 8 (Da Pontuação e Apuração do Campeonato, Arts. 31 a 35)
e a restrição de descarte do Art. 23, Parágrafo Único do Regulamento das Competições Cearenses.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Sequence

TABELA_PONTOS_COLOCACAO: tuple[int, ...] = (
    40, 37, 35, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24,
    23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11,
)

CATEGORIAS_ACOMPANHADAS: frozenset[str] = frozenset({
    'HN1', 'HN2', 'HN3', 'DN1', 'DN2', 'DN3',
})


@dataclass(frozen=True)
class ResultadoEtapaAtleta:
    """Representa o desempenho ou atuação de um atleta em uma etapa/percurso."""
    etapa: int
    categoria: str
    inscrito: bool = True
    concluiuPercurso: bool = False
    colocacao: int | None = None
    percursoAnulado: bool = False
    atuouComoVoluntario: bool = False
    penalizadoArt23: bool = False


def ehCategoriaSemPontuacao(categoria: str) -> bool:
    """Verifica se a categoria é Acompanhada ou Aberta (Regulamento, Art. 9º e Art. 31, § 3º)."""
    catLimpa = categoria.strip().upper()
    if catLimpa in CATEGORIAS_ACOMPANHADAS:
        return True
    return 'ACOMPANHAD' in catLimpa or 'ABERT' in catLimpa


def calcularPontosEtapa(
    categoria: str,
    concluiuPercurso: bool,
    colocacao: int | None,
    percursoAnulado: bool = False,
    participou: bool = True,
) -> int:
    """Calcula a pontuação individual em uma etapa/percurso (Regulamento, Art. 31 e ROP 21.5.1).

    - Categorias Acompanhado e percurso aberto: 0 pontos (Art. 31, § 3º).
    - Percurso anulado ou atleta não classificado que participou: 1 ponto (Art. 31, § 2º).
    - 1º ao 26º colocado: tabela progressiva de 40 a 11 pontos (Art. 31, caput).
    - 27º colocado em diante que concluiu o percurso: 10 pontos (Art. 31, § 1º).
    """
    if not participou or ehCategoriaSemPontuacao(categoria):
        return 0
    if percursoAnulado or not concluiuPercurso:
        return 1
    if colocacao is None or colocacao < 1:
        raise ValueError("Colocação deve ser um inteiro positivo quando o atleta conclui o percurso.")
    if colocacao <= len(TABELA_PONTOS_COLOCACAO):
        return TABELA_PONTOS_COLOCACAO[colocacao - 1]
    return 10


def temDireitoDescarteCCO(etapasRealizadasNoCampeonato: int) -> bool:
    """Define se há descarte obrigatório de 1 etapa no CCO (Regulamento, Art. 34, caput e § 1º)."""
    return etapasRealizadasNoCampeonato > 3


def exigirMinimoEtapasVoluntarioCCO(etapasRealizadasNoCampeonato: int) -> int:
    """Retorna o mínimo de etapas em que o voluntário precisa participar no CCO (Art. 33, § 1º).

    Considera apenas as etapas que realmente aconteceram, arredondando a metade para baixo.
    """
    return math.floor(etapasRealizadasNoCampeonato / 2)


def selecionarIndiceDescarte(
    pontosPorEtapa: Sequence[tuple[Decimal, bool]],
) -> int | None:
    """Seleciona o índice da etapa de menor pontuação passível de descarte (Art. 34 c/c Art. 23, Parágrafo Único).

    Recebe uma sequência de tuplas `(pontos, passivelDeDescarte)`.
    Retorna o índice da menor nota entre as passíveis de descarte, ou `None` se nenhuma puder ser descartada.
    """
    candidatos = [
        (pontos, idx)
        for idx, (pontos, passivel) in enumerate(pontosPorEtapa)
        if passivel
    ]
    if not candidatos:
        return None
    menorPontuacao = min(p for p, _ in candidatos)
    for pontos, idx in candidatos:
        if pontos == menorPontuacao:
            return idx
    return None


def arredondarPontuacao(valor: Decimal) -> Decimal:
    """Arredonda pontuação fracionária (média de voluntário) para 2 casas decimais."""
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcularMediaVoluntarioCCO(
    etapasRealizadasNoCampeonato: int,
    resultadosInscritosExcetoVoluntario: Sequence[tuple[int, bool]],
    participouEtapasTotais: int,
) -> Decimal:
    """Calcula a média de pontos do voluntário/árbitro no CCO (Regulamento, Art. 33, § 1º).

    - O atleta precisa participar de pelo menos `floor(etapasRealizadasNoCampeonato / 2)` etapas.
    - A média é calculada com base nas etapas em que o atleta se inscreveu (exceto a etapa de voluntário),
      aplicando-se previamente o descarte previsto no Art. 34 (quando o campeonato tiver > 3 etapas).
    """
    minimoExigido = exigirMinimoEtapasVoluntarioCCO(etapasRealizadasNoCampeonato)
    if participouEtapasTotais < minimoExigido or not resultadosInscritosExcetoVoluntario:
        return Decimal('0.00')

    notas = [
        (Decimal(pontos), passivelDescarte)
        for pontos, passivelDescarte in resultadosInscritosExcetoVoluntario
    ]

    if temDireitoDescarteCCO(etapasRealizadasNoCampeonato) and len(notas) > 1:
        idxDescarte = selecionarIndiceDescarte(notas)
        if idxDescarte is not None:
            notas = [item for idx, item in enumerate(notas) if idx != idxDescarte]

    soma = sum((p for p, _ in notas), Decimal('0'))
    return arredondarPontuacao(soma / Decimal(len(notas)))


def calcularPontuacaoClubeNaEtapa(
    pontosAtletasPorCategoria: dict[str, Sequence[tuple[Decimal, bool]]],
    clubeFiliadoCBO: bool = True,
) -> Decimal:
    """Calcula a pontuação de um clube em uma etapa/percurso (Regulamento, Art. 35).

    Soma os pontos dos seus 3 atletas filiados à CBO melhores classificados em cada categoria.
    Clubes não filiados à CBO não participam do resultado de clubes.
    """
    if not clubeFiliadoCBO:
        return Decimal('0.00')

    totalClube = Decimal('0.00')
    for _, listaAtletas in pontosAtletasPorCategoria.items():
        filiados = sorted(
            (pontos for pontos, atletaFiliado in listaAtletas if atletaFiliado),
            reverse=True,
        )
        totalClube += sum(filiados[:3], Decimal('0.00'))

    return arredondarPontuacao(totalClube)

