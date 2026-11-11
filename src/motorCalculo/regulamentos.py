# -*- coding: utf-8 -*-
"""Regras de apuração de cada edição, conforme o regulamento do próprio ano.

Este projeto complementa o repositório Regulamentos-de-Orientacao, que guarda um regulamento por
ano em `Documentos/<ano>/`. Cada edição é apurada pelo regulamento do seu ano: nenhuma regra vale
por herança de outro ano. Ano ou competição sem conjunto de regras registrado aqui não é apurado
(ADR-005).
"""
from dataclasses import dataclass
from typing import Literal

ArredondamentoMetade = Literal["baixo", "cima"]
CriterioDesempateIndividual = Literal["ultimoPercurso", "primeirosLugares"]
# Divisor da média do voluntário: só as outras etapas em que o atleta se inscreveu, ou todas as outras etapas
# realizadas (as sem inscrição e a outra etapa de apoio entram com 0 ponto).
DivisorMediaVoluntario = Literal["inscritas", "todasAsOutras"]
# Soma de clubes: os 3 melhores de cada categoria em cada etapa (texto do Art. 35 de 2026) ou os 3 melhores totais
# finais da categoria (método do resultado publicado de 2025, ADR-007).
SomaClubes = Literal["etapa", "totalDoCampeonato"]

TABELA_PONTOS_26_PRIMEIROS: tuple[int, ...] = (
    40, 37, 35, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24,
    23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11,
)


class RegulamentoNaoMapeadoError(ValueError):
    """Ano ou competição sem regras de apuração registradas em `regulamentos.py`."""


@dataclass(frozen=True)
class ArtigosRegulamento:
    """Citação dos dispositivos do regulamento do ano, usada nos relatórios e docstrings."""
    pontuacao: str
    trocaCategoria: str
    voluntarios: str
    voluntariosMinimo: str
    classificacaoGeral: str
    desempateIndividual: str
    clubes: str
    desempateClubes: str
    premiacao: str
    penalidadeChegada: str
    percursoAnulado: str
    naoClassificado: str
    descarte: str | None = None


@dataclass(frozen=True)
class RegrasRegulamento:
    """Conjunto imutável das regras de apuração de uma competição em um ano."""
    ano: int
    competicao: str
    nomeRegulamento: str
    arquivoFonte: str
    artigos: ArtigosRegulamento
    tabelaPontos: tuple[int, ...]
    pontosDaPosicaoSeguinteEmDiante: int
    pontosParticipacao: int
    # Há descarte quando as etapas realizadas forem MAIS que este valor; `None` = nunca há descarte.
    etapasRealizadasParaDescarte: int | None
    # Mínimo de etapas (voluntário e premiação) = metade das etapas realizadas, arredondada assim.
    minimoMetadeArredondaPara: ArredondamentoMetade
    # `True`: a etapa de voluntário/árbitro conta no mínimo exigido ao voluntário ("participar").
    # `False`: só conta etapa em que o atleta competiu ("competir").
    voluntarioContaEtapaDeApoioNoMinimo: bool
    mediaVoluntarioDivideEntre: DivisorMediaVoluntario
    # `True`: cada média de voluntário é arredondada a 2 casas antes de somar (2026).
    # `False`: a média entra com a fração exata e só o total é arredondado (resultado publicado de 2025).
    arredondaMediaVoluntario: bool
    desempateIndividual: CriterioDesempateIndividual
    clubeSomaTop3Por: SomaClubes

    @property
    def temDescarte(self) -> bool:
        """Indica se o regulamento do ano prevê algum descarte de etapa."""
        return self.etapasRealizadasParaDescarte is not None

    @property
    def rotulo(self) -> str:
        """Identificação curta da competição e do ano (ex.: `CCO 2025`)."""
        return f"{self.competicao} {self.ano}"


REGRAS_CCO_2025 = RegrasRegulamento(
    ano=2025,
    competicao="CCO",
    nomeRegulamento="Regulamento do XIX Campeonato Cearense de Orientação (2025)",
    arquivoFonte="Documentos/2025/regulamentoCCO.md",
    artigos=ArtigosRegulamento(
        pontuacao="Art. 34",
        trocaCategoria="Art. 35",
        voluntarios="Art. 36",
        voluntariosMinimo="Art. 36, § 1º",
        classificacaoGeral="Art. 38",
        desempateIndividual="Art. 38, Parágrafo Único",
        clubes="Art. 37",
        desempateClubes="Art. 39, Parágrafo Único",
        premiacao="Art. 42, § 1º",
        penalidadeChegada="Art. 20, Parágrafo Único",
        percursoAnulado="Art. 34, § 1º",
        naoClassificado="Art. 34, § 2º",
        descarte=None,
    ),
    tabelaPontos=TABELA_PONTOS_26_PRIMEIROS,
    pontosDaPosicaoSeguinteEmDiante=10,
    pontosParticipacao=1,
    etapasRealizadasParaDescarte=None,
    minimoMetadeArredondaPara="cima",
    # Confirmado pelo resultado oficial publicado de 2025 (ADR-005): a etapa de apoio conta no mínimo e a média
    # divide por todas as outras etapas (ex.: um único resultado de 35 pontos rende 35/3 = 11,67 de média).
    voluntarioContaEtapaDeApoioNoMinimo=True,
    mediaVoluntarioDivideEntre="todasAsOutras",
    arredondaMediaVoluntario=False,
    desempateIndividual="primeirosLugares",
    # O Art. 37 fala em "por etapa", mas o resultado publicado (que vale, ADR-007) soma os 3 melhores totais finais.
    clubeSomaTop3Por="totalDoCampeonato",
)

REGRAS_CCO_2026 = RegrasRegulamento(
    ano=2026,
    competicao="CCO",
    nomeRegulamento="Regulamento das Competições Cearenses de Orientação (2026)",
    arquivoFonte="Documentos/2026/regulamentoDasCompeticoesCearenses.md",
    artigos=ArtigosRegulamento(
        pontuacao="Art. 31",
        trocaCategoria="Art. 32",
        voluntarios="Art. 33",
        voluntariosMinimo="Art. 33, § 1º",
        classificacaoGeral="Art. 34",
        desempateIndividual="Art. 34, § 2º",
        clubes="Art. 35",
        desempateClubes="Art. 35, Parágrafo Único",
        premiacao="Art. 39, § 1º",
        penalidadeChegada="Art. 23, Parágrafo Único",
        percursoAnulado="Art. 31, § 2º",
        naoClassificado="Art. 31, § 2º",
        descarte="Art. 34",
    ),
    tabelaPontos=TABELA_PONTOS_26_PRIMEIROS,
    pontosDaPosicaoSeguinteEmDiante=10,
    pontosParticipacao=1,
    etapasRealizadasParaDescarte=3,
    minimoMetadeArredondaPara="baixo",
    voluntarioContaEtapaDeApoioNoMinimo=True,
    mediaVoluntarioDivideEntre="inscritas",
    arredondaMediaVoluntario=True,
    desempateIndividual="ultimoPercurso",
    clubeSomaTop3Por="etapa",
)

REGRAS_POR_EDICAO: dict[tuple[int, str], RegrasRegulamento] = {
    (r.ano, r.competicao): r for r in (REGRAS_CCO_2025, REGRAS_CCO_2026)
}


def anosMapeados() -> list[int]:
    """Lista, em ordem crescente, os anos que têm regras registradas para alguma competição."""
    return sorted({ano for ano, _ in REGRAS_POR_EDICAO})


def obterRegras(ano: int, competicao: str = "CCO") -> RegrasRegulamento:
    """Retorna as regras do regulamento do ano e da competição, ou recusa se não houver.

    Não há regra padrão nem ano substituto: cada edição é apurada pelo seu próprio regulamento.
    """
    regras = REGRAS_POR_EDICAO.get((ano, competicao.upper()))
    if regras is None:
        mapeados = ", ".join(f"{c} {a}" for a, c in sorted(REGRAS_POR_EDICAO)) or "nenhum"
        raise RegulamentoNaoMapeadoError(
            f"Regras do {competicao.upper()} {ano} não registradas em src/motorCalculo/regulamentos.py "
            f"(mapeados: {mapeados}). Leia Documentos/{ano}/ no repositório Regulamentos-de-Orientacao, "
            "registre as regras, atualize a spec scoring-engine e crie os testes antes de apurar."
        )
    return regras


def calcularMinimoMetadeEtapas(etapasRealizadas: int, regras: RegrasRegulamento) -> int:
    """Calcula o mínimo de etapas equivalente à metade das realizadas, conforme o arredondamento do ano.

    2026, Art. 33, § 1º: arredonda para baixo. 2025, Art. 36, § 1º e Art. 42, § 1º: o regulamento é
    omisso e adota-se a leitura literal de "no mínimo a metade" (arredonda para cima; ADR-005).
    """
    if regras.minimoMetadeArredondaPara == "baixo":
        return etapasRealizadas // 2
    return (etapasRealizadas + 1) // 2
