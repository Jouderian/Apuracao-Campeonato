# -*- coding: utf-8 -*-
"""Escopo da análise de desempenho (spec analise-desempenho).

Categorias não competitivas do regulamento do ano ficam fora de todas as extrações e da base, porque trazem muito
ruído nos tempos e nas leituras (decisão do apurador, 2026-11-14). São as acompanhadas (`HN1` a `HN3` e `DN1` a
`DN3`), sem classificação (Art. 22 em 2024 e 2025; Art. 9º em 2026), e o percurso aberto, que não pontua
(Art. 34, § 3º em 2024 e 2025; Art. 31, § 3º em 2026). Os três regulamentos dizem o mesmo; um ano novo com regra
diferente exige rever esta decisão. Reaproveita a verificação do motor de cálculo, para não haver duas definições.
"""
from src.motorCalculo.pontuacao import ehCategoriaSemPontuacao


def ehCategoriaNaoCompetitiva(categoria: str) -> bool:
    """Verdadeiro para categoria acompanhada ou aberta, que a análise ignora."""
    return ehCategoriaSemPontuacao(categoria)
