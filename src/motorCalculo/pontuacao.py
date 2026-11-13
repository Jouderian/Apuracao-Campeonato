# -*- coding: utf-8 -*-
"""Regras puras de pontuação e apuração do Campeonato Cearense de Orientação (CCO e CCOS).

Implementa a pontuação, o descarte, a média de voluntários, a pontuação de clubes e os desempates
conforme o regulamento do ano da edição, recebido como `RegrasRegulamento` (ver `regulamentos.py`).
Nenhuma regra vale por herança de outro ano (ADR-005). Os artigos citados nas docstrings são os de
2026 (Arts. 23, 31 a 35 e 39); os de 2025 (Arts. 20, 34 a 42) constam em `regulamentos.py`.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections.abc import Sequence
from typing import Any

from src.motorCalculo.regulamentos import RegrasRegulamento, calcularMinimoMetadeEtapas

CATEGORIAS_ACOMPANHADAS: frozenset[str] = frozenset({
    'HN1', 'HN2', 'HN3', 'DN1', 'DN2', 'DN3',
})

# Códigos de status na tabela Status do software Helga:
STATUS_OK = 0
STATUS_NC = 1
STATUS_DC = 2
STATUS_NP = 3
STATUS_NT = 4
STATUS_OT = 5
STATUS_DNF = 6
STATUS_FIN = 7
STATUS_CC = 98

# Status que representam que o atleta largou/participou mas não se classificou (1 ponto pelo Art. 31, § 2º):
STATUS_NAO_CLASSIFICADO_COM_PONTO: frozenset[int] = frozenset({
    STATUS_NC, STATUS_DC, STATUS_NT, STATUS_OT, STATUS_DNF,
})

# Status que representam não participação / cancelamento de inscrição (0 pontos):
STATUS_SEM_PARTICIPACAO: frozenset[int] = frozenset({
    STATUS_NP, STATUS_CC,
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


@dataclass
class DesempenhoEtapaCalculado:
    """Memória de cálculo de um atleta em uma etapa específica dentro de uma categoria."""
    etapa: int
    inscrito: bool = False
    participou: bool = False
    atuouComoVoluntario: bool = False
    direitoMediaVoluntario: bool = False
    statusCodigo: int | None = None
    statusSigla: str = "-"
    tempo: str | None = None
    colocacao: int | None = None
    pontosBrutos: Decimal = Decimal('0.00')
    pontosFinais: Decimal = Decimal('0.00')
    descartada: bool = False
    passivelDescarte: bool = True
    ajustadoOficial: bool = False   # nota substituída pelo valor do resultado oficial publicado (ADR-007)
    destaqueMedia: bool = False     # nota ajustada que o publicado destaca como média (amarelo)


@dataclass
class ClassificacaoAtletaCategoria:
    """Resultado consolidado de um atleta em uma categoria no campeonato."""
    cbo: int
    nome: str
    clubeId: int
    clubeSigla: str
    clubeNome: str
    clubeFiliadoCBO: bool
    categoria: str
    etapas: dict[int, DesempenhoEtapaCalculado] = field(default_factory=dict)
    etapaDescartada: int | None = None
    pontuacaoTotal: Decimal = Decimal('0.00')
    etapasParticipadas: int = 0
    elegivelPremiacao: bool = False
    colocacaoFinal: int = 0
    colocacaoNaCategoria: int = 0
    categoriaValidaFinal: bool = True
    competiuEmMultiplasCategorias: bool = False
    empateNaoResolvido: bool = False


MAPA_CATEGORIA_PADRAO_CBO: dict[str, str] = {
    "D10N": "D Infant N", "D12N": "D Infant N", "D12B": "D Infant B",
    "D14N": "D Juven N", "D14B": "D Juven B", "D14A": "D Juven A",
    "D16N": "D Juven N", "D16B": "D Juven B", "D16A": "D Juven A",
    "D18N": "D Juven N", "D18B": "D Juven B", "D18A": "D Juven A",
    "D20N": "D Junior N", "D20B": "D Junior B", "D20A": "D Junior A", "D20E": "D Junior E",
    "D21N": "D Adulto N", "D21B": "D Adulto B", "D21A": "D Adulto A", "D21E": "D Adulto E",
    "D35N": "D Master N", "D35B": "D Master B", "D35A": "D Master A",
    "D40N": "D Master N", "D40B": "D Master B", "D40A": "D Master A",
    "D45N": "D Sênior N", "D45B": "D Sênior B", "D45A": "D Sênior A",
    "D50N": "D Sênior N", "D50B": "D Sênior B", "D50A": "D Sênior A",
    "D55N": "D Vet N", "D55B": "D Vet B", "D55A": "D Vet A",
    "D60N": "D Vet N", "D60B": "D Vet B", "D60A": "D Vet A",
    "H10N": "H Infant N", "H12N": "H Infant N", "H12B": "H Infant B",
    "H14N": "H Juven N", "H14B": "H Juven B", "H14A": "H Juven A",
    "H16N": "H Juven N", "H16B": "H Juven B", "H16A": "H Juven A",
    "H18N": "H Juven N", "H18B": "H Juven B", "H18A": "H Juven A",
    "H20N": "H Junior N", "H20B": "H Junior B", "H20A": "H Junior A", "H20E": "H Junior E",
    "H21N": "H Adulto N", "H21B": "H Adulto B", "H21A": "H Adulto A", "H21E": "H Adulto E",
    "H35N": "H Master N", "H35B": "H Master B", "H35A": "H Master A",
    "H40N": "H Master N", "H40B": "H Master B", "H40A": "H Master A",
    "H45N": "H Sênior N", "H45B": "H Sênior B", "H45A": "H Sênior A",
    "H50N": "H Sênior N", "H50B": "H Sênior B", "H50A": "H Sênior A",
    "H55N": "H Vet N", "H55B": "H Vet B", "H55A": "H Vet A",
    "H60N": "H Vet N", "H60B": "H Vet B", "H60A": "H Vet A",
}


def normalizarCategoriaPadraoCBO(categoria: str) -> str:
    """Converte código CBO da tabela Runners (ex.: D21B) para categoria aglutinada do CCO quando aplicável."""
    limpa = categoria.strip()
    return MAPA_CATEGORIA_PADRAO_CBO.get(limpa.upper(), limpa)



def ehCategoriaSemPontuacao(categoria: str) -> bool:
    """Verifica se a categoria é Acompanhada ou Aberta (Regulamento 2026, Art. 9º e Art. 31, § 3º)."""
    catLimpa = categoria.strip().upper()
    if catLimpa in CATEGORIAS_ACOMPANHADAS:
        return True
    return 'ACOMPANHAD' in catLimpa or 'ABERT' in catLimpa


def atletaFiliadoCBO(cbo: int) -> bool:
    """Verifica se o identificador CBO corresponde a registro oficial na CBO (Regulamento 2026, Art. 2º, § 2º).

    No Helga, inscrições avulsas de não filiados recebem códigos provisórios >= 100000 (ex.: 116xxx, 990xxx, 999xxx).
    """
    return 0 < cbo < 100000


def calcularPontosEtapa(
    categoria: str,
    concluiuPercurso: bool,
    colocacao: int | None,
    percursoAnulado: bool = False,
    participou: bool = True,
    *,
    regras: RegrasRegulamento,
) -> int:
    """Calcula a pontuação individual em uma etapa/percurso (Regulamento 2026, Art. 31 e ROP 21.5.1; 2025, Art. 34).

    - Categorias Acompanhado e percurso aberto: 0 pontos (Art. 31, § 3º).
    - Percurso anulado ou atleta não classificado que participou (NC, OT, DNF, DC): 1 ponto (Art. 31, § 2º).
    - 1º ao 26º colocado: tabela progressiva de 40 a 11 pontos (Art. 31, caput).
    - 27º colocado em diante que concluiu o percurso: 10 pontos (Art. 31, § 1º).
    Os valores vêm do regulamento do ano (`regras`).
    """
    if not participou or ehCategoriaSemPontuacao(categoria):
        return 0
    if percursoAnulado or not concluiuPercurso:
        return regras.pontosParticipacao
    if colocacao is None or colocacao < 1:
        raise ValueError("Colocação deve ser um inteiro positivo quando o atleta conclui o percurso.")
    if colocacao <= len(regras.tabelaPontos):
        return regras.tabelaPontos[colocacao - 1]
    return regras.pontosDaPosicaoSeguinteEmDiante


def calcularPontosStatusHelga(
    categoria: str,
    statusCodigo: int,
    colocacao: int | None,
    percursoAnulado: bool = False,
    *,
    regras: RegrasRegulamento,
) -> int:
    """Traduz o Status_FK do Helga para a pontuação da etapa (Regulamento 2026, Art. 31; 2025, Art. 34)."""
    if statusCodigo in STATUS_SEM_PARTICIPACAO:
        return 0
    if statusCodigo == STATUS_OK:
        return calcularPontosEtapa(
            categoria=categoria,
            concluiuPercurso=True,
            colocacao=colocacao,
            percursoAnulado=percursoAnulado,
            participou=True,
            regras=regras,
        )
    if statusCodigo in STATUS_NAO_CLASSIFICADO_COM_PONTO:
        return calcularPontosEtapa(
            categoria=categoria,
            concluiuPercurso=False,
            colocacao=None,
            percursoAnulado=percursoAnulado,
            participou=True,
            regras=regras,
        )
    return 0


def temDireitoDescarteCCO(etapasRealizadasNoCampeonato: int, regras: RegrasRegulamento) -> bool:
    """Define se há descarte de 1 etapa no CCO (Regulamento 2026, Art. 34, caput e § 1º).

    2026: descarte obrigatório quando houver mais de 3 etapas realizadas. 2025: nunca há descarte
    (Art. 38, "sem descartes").
    """
    limite = regras.etapasRealizadasParaDescarte
    return limite is not None and etapasRealizadasNoCampeonato > limite


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
    resultadosInscritosExcetoVoluntario: Sequence[tuple[int | Decimal, bool]],
    participouEtapasTotais: int,
    *,
    regras: RegrasRegulamento,
) -> Decimal:
    """Calcula a média de pontos do voluntário/árbitro no CCO (Regulamento 2026, Art. 33, § 1º; 2025, Art. 36).

    - O atleta precisa atingir a metade das etapas realizadas (2026: arredondada para baixo; 2025: para cima).
    - A média é calculada com base nas notas recebidas (as etapas em que o atleta se inscreveu em 2026; todas as
      outras etapas realizadas em 2025), aplicando-se previamente o descarte do Art. 34 somente quando o
      regulamento do ano o prevê (2026, campeonato com > 3 etapas); em 2025 não há descarte.
    """
    minimoExigido = calcularMinimoMetadeEtapas(etapasRealizadasNoCampeonato, regras)
    if participouEtapasTotais < minimoExigido or not resultadosInscritosExcetoVoluntario:
        return Decimal('0.00')

    notas = [
        (Decimal(pontos), passivelDescarte)
        for pontos, passivelDescarte in resultadosInscritosExcetoVoluntario
    ]

    if temDireitoDescarteCCO(etapasRealizadasNoCampeonato, regras) and len(notas) > 1:
        idxDescarte = selecionarIndiceDescarte(notas)
        if idxDescarte is not None:
            notas = [item for idx, item in enumerate(notas) if idx != idxDescarte]

    soma = sum((p for p, _ in notas), Decimal('0'))
    media = soma / Decimal(len(notas))
    return arredondarPontuacao(media) if regras.arredondaMediaVoluntario else media


def calcularPontuacaoClubeNaEtapa(
    pontosAtletasPorCategoria: dict[str, Sequence[tuple[Decimal, bool]]],
    clubeFiliadoCBO: bool = True,
) -> Decimal:
    """Calcula a pontuação de um clube em uma etapa/percurso (Regulamento 2026, Art. 35).

    Soma os pontos dos seus 3 atletas filiados à CBO melhores classificados em cada categoria.
    Clubes não filiados à CBO não participam do resultado de clubes.
    """
    if not clubeFiliadoCBO:
        return Decimal('0.00')

    totalClube = Decimal('0.00')
    for _, listaAtletas in pontosAtletasPorCategoria.items():
        filiados = sorted(
            (pontos for pontos, atletaEhFiliado in listaAtletas if atletaEhFiliado and pontos > 0),
            reverse=True,
        )
        totalClube += sum(filiados[:3], Decimal('0.00'))

    return arredondarPontuacao(totalClube)


def diagnosticarEtapas(dadosHelga: dict[str, Any]) -> list[str]:
    """Aponta etapas ausentes do banco ou sem nenhum resultado, que distorcem o total de etapas realizadas.

    O total de etapas realizadas decide o descarte (2026) e o mínimo de etapas de voluntários e de premiação.
    Etapa do calendário ausente do banco, ou presente só com inscrições NP/CC, não pode ser tratada como
    realizada sem conferência do apurador.
    """
    numeros = sorted(int(e["numeroEtapa"]) for e in dadosHelga["etapas"])
    avisos: list[str] = []
    ausentes = [n for n in range(1, (numeros[-1] if numeros else 0) + 1) if n not in numeros]
    if ausentes:
        lista = ", ".join(f"{n}ª" for n in ausentes)
        avisos.append(
            f"etapa(s) {lista} ausente(s) do banco: não entram na apuração nem no total de etapas realizadas; "
            "confirme se foram canceladas ou se falta o banco delas"
        )
    for numero in numeros:
        registros = [r for r in dadosHelga["registrosEtapas"] if int(r["etapa"]) == numero]
        if not any(int(r["statusCodigo"]) not in STATUS_SEM_PARTICIPACAO for r in registros):
            avisos.append(
                f"{numero}ª etapa sem nenhum resultado ({len(registros)} inscrições, todas NP/CC): "
                "é contada como realizada; confirme se o banco traz os resultados dela"
            )
    return avisos


def _ehClassificavel(ficha: ClassificacaoAtletaCategoria) -> bool:
    """Indica se a ficha disputa colocação final (categoria válida após troca e com pontos)."""
    return ficha.categoriaValidaFinal and ficha.pontuacaoTotal > 0


def ordenarCategoriaPorUltimoPercurso(
    lista: list[ClassificacaoAtletaCategoria],
    numerosEtapas: Sequence[int],
    sinalizarEmpates: bool,
) -> None:
    """Ordena a categoria pelo desempate de 2026 (Regulamento 2026, Art. 34, § 2º).

    Total de pontos; empatando, melhor resultado no último percurso e, sucessivamente, nos anteriores.
    O critério de maior idade não é aplicado (ADR-003): o empate restante é sinalizado.
    """
    etapasReversas = list(reversed(numerosEtapas))

    def chaveOrdenacaoIndividual(f: ClassificacaoAtletaCategoria) -> tuple[Any, ...]:
        notasReversas = tuple(f.etapas[et].pontosFinais for et in etapasReversas)
        return (f.pontuacaoTotal, *notasReversas, -f.cbo)

    lista.sort(key=chaveOrdenacaoIndividual, reverse=True)
    if not sinalizarEmpates:
        return
    classificaveis = [f for f in lista if _ehClassificavel(f)]
    for anterior, atual in zip(classificaveis, classificaveis[1:], strict=False):
        # Compara todos os critérios do regulamento (a chave sem o CBO final).
        if chaveOrdenacaoIndividual(anterior)[:-1] == chaveOrdenacaoIndividual(atual)[:-1]:
            anterior.empateNaoResolvido = True
            atual.empateNaoResolvido = True


def desempatarPorConfrontoDireto(
    grupo: Sequence[ClassificacaoAtletaCategoria],
    numerosEtapas: Sequence[int],
) -> list[ClassificacaoAtletaCategoria] | None:
    """Ordena atletas empatados pelo último confronto direto (Regulamento 2025, Art. 38, Parágrafo Único, "b").

    Vale a etapa mais recente em que todos os empatados foram classificados (têm colocação) na categoria;
    vence a melhor colocação nela. Sem etapa assim, retorna `None` e o empate segue sem resolução
    automática (ADR-005).
    """
    for etapa in reversed(numerosEtapas):
        colocacoes = [f.etapas[etapa].colocacao for f in grupo]
        if all(c is not None for c in colocacoes):
            return sorted(grupo, key=lambda f: f.etapas[etapa].colocacao or 0)
    return None


def ordenarCategoriaPorPrimeirosLugares(
    lista: list[ClassificacaoAtletaCategoria],
    numerosEtapas: Sequence[int],
    sinalizarEmpates: bool,
) -> None:
    """Ordena a categoria pelo desempate de 2025 (Regulamento 2025, Art. 38, Parágrafo Único).

    Total de pontos; empatando, maior número de 1ºs lugares, depois de 2ºs e assim sucessivamente;
    persistindo, melhor resultado no último confronto direto. O critério de maior idade não é aplicado
    (ADR-003): o empate restante é sinalizado.
    """
    maiorColocacao = max(
        (d.colocacao for f in lista for d in f.etapas.values() if d.colocacao),
        default=1,
    )

    def contagemColocacoes(f: ClassificacaoAtletaCategoria) -> tuple[int, ...]:
        return tuple(
            sum(1 for d in f.etapas.values() if d.colocacao == posicao and not d.descartada)
            for posicao in range(1, maiorColocacao + 1)
        )

    def chaveSemCbo(f: ClassificacaoAtletaCategoria) -> tuple[Any, ...]:
        return (f.pontuacaoTotal, contagemColocacoes(f))

    lista.sort(key=lambda f: (*chaveSemCbo(f), -f.cbo), reverse=True)
    if not sinalizarEmpates:
        return

    classificaveis = [f for f in lista if _ehClassificavel(f)]
    grupos: list[list[ClassificacaoAtletaCategoria]] = []
    for ficha in classificaveis:
        if grupos and chaveSemCbo(grupos[-1][0]) == chaveSemCbo(ficha):
            grupos[-1].append(ficha)
        else:
            grupos.append([ficha])

    posicoes = {id(f): idx for idx, f in enumerate(lista)}
    for grupo in grupos:
        if len(grupo) < 2:
            continue
        ordem = desempatarPorConfrontoDireto(grupo, numerosEtapas)
        if ordem is None:
            for f in grupo:
                f.empateNaoResolvido = True
            continue
        for casa, f in zip(sorted(posicoes[id(g)] for g in grupo), ordem, strict=True):
            lista[casa] = f


def aplicarPosicoesOficiais(
    lista: list[ClassificacaoAtletaCategoria],
    categoria: str,
    posicoesOficiais: dict[tuple[int, str], int],
    aplicadas: set[tuple[int, str]],
) -> None:
    """Coloca nas posições decididas pela FECORI os atletas listados (ADR-008).

    Os demais mantêm a ordem calculada. O atleta com posição decidida deixa de ter empate pendente,
    pois a FECORI já o resolveu (por critério que o repositório não aplica, como a idade, ADR-003).
    """
    marcados = [(posicoesOficiais[(f.cbo, categoria)], f) for f in lista if (f.cbo, categoria) in posicoesOficiais]
    if not marcados:
        return
    posicoes = [p for p, _ in marcados]
    if len(set(posicoes)) != len(posicoes) or max(posicoes) > len(lista):
        raise ValueError(f"posições oficiais inválidas em {categoria}: {sorted(posicoes)} (categoria com {len(lista)} fichas)")
    resto = [f for f in lista if (f.cbo, categoria) not in posicoesOficiais]
    for posicao, ficha in sorted(marcados, key=lambda item: item[0]):
        resto.insert(posicao - 1, ficha)
        ficha.empateNaoResolvido = False
        aplicadas.add((ficha.cbo, categoria))
    lista[:] = resto


def apurarCampeonatoCCO(
    dadosHelga: dict[str, Any],
    dadosVoluntarios: dict[str, Any],
    regras: RegrasRegulamento,
) -> dict[str, Any]:
    """Executa a apuração completa do CCO pelo regulamento do ano recebido em `regras`.

    2026: Arts. 23, 31 a 35 e 39. 2025: Arts. 20, 34 a 42 (sem descarte). As regras de cada ano estão
    em `regulamentos.py`; não há regra padrão (ADR-005).
    """
    etapasInfo = sorted(dadosHelga["etapas"], key=lambda e: e["numeroEtapa"])
    numerosEtapas = [e["numeroEtapa"] for e in etapasInfo]
    totalEtapasRealizadas = len(numerosEtapas)
    minimoEtapasPremiacaoEVoluntario = calcularMinimoMetadeEtapas(totalEtapasRealizadas, regras)
    descarteAplicado = temDireitoDescarteCCO(totalEtapasRealizadas, regras)

    mapaUnificacaoCbo: dict[int, int] = {
        int(u["cboProvisorio"]): int(u["cboOficial"])
        for u in dadosVoluntarios.get("unificacoesCbo", [])
    }

    # Só entram etapas presentes nos dados: etapa ausente do banco não é apurada.
    # Clube oficial declarado na unificação: vale quando o CBO oficial não consta no cadastro do banco.
    clubesPorSigla = {str(c["sigla"]).strip().upper(): c for c in dadosHelga["clubes"]}
    clubeDaUnificacao: dict[int, dict[str, Any]] = {}
    for u in dadosVoluntarios.get("unificacoesCbo", []):
        clube = clubesPorSigla.get(str(u.get("clubeSigla", "")).strip().upper())
        if clube is not None:
            clubeDaUnificacao[int(u["cboOficial"])] = clube

    voluntariosSet: set[tuple[int, int]] = {
        (int(v["etapa"]), mapaUnificacaoCbo.get(int(v["cbo"]), int(v["cbo"])))
        for v in dadosVoluntarios.get("voluntarios", [])
        if int(v["etapa"]) in numerosEtapas
    }
    penalidadesArt23Set: set[tuple[int, int]] = {
        (int(p["etapa"]), mapaUnificacaoCbo.get(int(p["cbo"]), int(p["cbo"])))
        for p in dadosVoluntarios.get("penalidadesArt23", [])
        if int(p["etapa"]) in numerosEtapas
    }

    # Ajustes do resultado oficial publicado (ADR-007): (etapa, CBO oficial, categoria) -> pontos publicados.
    ajustesOficiais: dict[tuple[int, int, str], Decimal] = {}
    ajustesComDestaqueMedia: set[tuple[int, int, str]] = set()
    for a in dadosVoluntarios.get("ajustesOficiais", []):
        try:
            pontosAjuste = Decimal(str(a["pontos"]).strip().replace(",", "."))
        except InvalidOperation as erro:
            raise ValueError(f"ajuste oficial com pontos inválidos: {a!r}") from erro
        if not Decimal("0") <= pontosAjuste <= Decimal("40"):
            raise ValueError(f"ajuste oficial com pontos fora de 0 a 40: {a!r}")
        if int(a["etapa"]) not in numerosEtapas:
            raise ValueError(f"ajuste oficial de etapa ausente da apuração: {a!r}")
        chaveAjuste = (int(a["etapa"]), mapaUnificacaoCbo.get(int(a["cbo"]), int(a["cbo"])), str(a["categoria"]).strip())
        if chaveAjuste in ajustesOficiais:
            raise ValueError(f"ajuste oficial repetido: {a!r}")
        destaqueAjuste = str(a.get("destaque", "")).strip().lower()
        if destaqueAjuste not in ("", "média", "media"):
            raise ValueError(f"ajuste oficial com destaque desconhecido (use 'média' ou deixe vazio): {a!r}")
        ajustesOficiais[chaveAjuste] = arredondarPontuacao(pontosAjuste)
        if destaqueAjuste:
            ajustesComDestaqueMedia.add(chaveAjuste)
    ajustesAplicados: set[tuple[int, int, str]] = set()

    # Posições do resultado oficial publicado (ADR-007): (CBO oficial, categoria) -> posição na categoria.
    posicoesOficiais: dict[tuple[int, str], int] = {}
    for a in dadosVoluntarios.get("posicoesOficiais", []):
        chavePos = (mapaUnificacaoCbo.get(int(a["cbo"]), int(a["cbo"])), str(a["categoria"]).strip())
        if chavePos in posicoesOficiais or int(a["posicao"]) < 1:
            raise ValueError(f"posição oficial repetida ou inválida: {a!r}")
        posicoesOficiais[chavePos] = int(a["posicao"])
    posicoesAplicadas: set[tuple[int, str]] = set()

    # Atletas que o resultado oficial publicado não lista (ADR-007): (CBO oficial, categoria).
    omissoesOficiais: set[tuple[int, str]] = {
        (mapaUnificacaoCbo.get(int(o["cbo"]), int(o["cbo"])), str(o["categoria"]).strip())
        for o in dadosVoluntarios.get("omissoesOficiais", [])
    }

    perfis = dadosHelga["perfisAtletas"]
    registrosOriginais = dadosHelga["registrosEtapas"]

    perfisOficiaisFallback: dict[int, dict[str, Any]] = {}
    for r in registrosOriginais:
        cboReg = int(r["cbo"])
        if cboReg not in perfisOficiaisFallback:
            perfisOficiaisFallback[cboReg] = r

    registros: list[dict[str, Any]] = []
    for r in registrosOriginais:
        cboOrig = int(r["cbo"])
        if cboOrig in mapaUnificacaoCbo:
            cboOficial = mapaUnificacaoCbo[cboOrig]
            baseOficial = perfis.get(str(cboOficial)) or perfisOficiaisFallback.get(cboOficial, {})
            rUnificado = dict(r)
            rUnificado["cbo"] = cboOficial
            clubeDeclarado = clubeDaUnificacao.get(cboOficial)
            if not baseOficial and clubeDeclarado is not None:
                rUnificado["clubeId"] = clubeDeclarado["clubeId"]
                rUnificado["clubeSigla"] = clubeDeclarado["sigla"]
                rUnificado["clubeNome"] = clubeDeclarado["nome"]
                rUnificado["clubeFiliadoCBO"] = bool(clubeDeclarado.get("filiadoCBO", False))
            if baseOficial:
                rUnificado["nome"] = baseOficial.get("nome", r["nome"])
                rUnificado["clubeId"] = baseOficial.get("clubeId", r["clubeId"])
                rUnificado["clubeSigla"] = baseOficial.get("clubeSigla", r["clubeSigla"])
                rUnificado["clubeNome"] = baseOficial.get("clubeNome", r["clubeNome"])
                rUnificado["clubeFiliadoCBO"] = baseOficial.get("clubeFiliadoCBO", r["clubeFiliadoCBO"])
            registros.append(rUnificado)
        else:
            registros.append(r)

    # 1. Calcular colocações dentro de cada etapa e categoria (Status_FK == 0 e ClassifyYN == True, ordenado por tempo)
    porEtapaCategoria: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for reg in registros:
        chave = (int(reg["etapa"]), reg["categoria"])
        porEtapaCategoria.setdefault(chave, []).append(reg)

    colocacoesNaEtapa: dict[tuple[int, str, int], int] = {}
    for (etapaNum, categoria), listaRegs in porEtapaCategoria.items():
        if ehCategoriaSemPontuacao(categoria):
            continue
        classificados = [
            r for r in listaRegs
            if int(r["statusCodigo"]) == STATUS_OK and r.get("classifyYN", True)
        ]
        classificados.sort(
            key=lambda r: (
                r["tempoSegundos"] if r["tempoSegundos"] is not None else 999999,
                r.get("tempoMs", 0),
                r["runnerPk"],
            )
        )
        for pos, r in enumerate(classificados, start=1):
            colocacoesNaEtapa[(etapaNum, categoria, int(r["cbo"]))] = pos

    # 2. Agrupar inscrições por (cbo, categoria)
    inscricoesPorAtletaCat: dict[tuple[int, str], dict[int, dict[str, Any]]] = {}
    categoriasDoAtleta: dict[int, set[str]] = {}
    for reg in registros:
        cbo = int(reg["cbo"])
        cat = reg["categoria"]
        etapaNum = int(reg["etapa"])
        inscricoesPorAtletaCat.setdefault((cbo, cat), {})[etapaNum] = reg
        categoriasDoAtleta.setdefault(cbo, set()).add(cat)

    # Garantir que voluntários que não estavam inscritos na tabela Course naquela etapa entrem na sua categoria
    for _etapaVol, cboVol in sorted(voluntariosSet):
        cats = categoriasDoAtleta.get(cboVol)
        if cats:
            catAlvo = sorted(cats)[0]
        else:
            perfilVol = perfis.get(str(cboVol), {})
            catAlvo = normalizarCategoriaPadraoCBO(perfilVol.get("categoriaPadrao") or "Sem Categoria")
            categoriasDoAtleta.setdefault(cboVol, set()).add(catAlvo)
        inscricoesPorAtletaCat.setdefault((cboVol, catAlvo), {})

    # 3. Construir fichas por (cbo, categoria)
    fichasPorAtletaCat: list[ClassificacaoAtletaCategoria] = []
    for (cbo, categoria), mapaEtapas in sorted(inscricoesPorAtletaCat.items()):
        amostraReg = next(iter(mapaEtapas.values()), None)
        perfil = perfis.get(str(cbo), {})
        nome = (amostraReg["nome"] if amostraReg else perfil.get("nome", f"CBO {cbo}"))
        clubeId = int(amostraReg["clubeId"] if amostraReg else perfil.get("clubeId", 0))
        clubeSigla = (amostraReg["clubeSigla"] if amostraReg else perfil.get("clubeSigla", ""))
        clubeNome = (amostraReg["clubeNome"] if amostraReg else perfil.get("clubeNome", ""))
        clubeFiliado = bool(amostraReg["clubeFiliadoCBO"] if amostraReg else perfil.get("clubeFiliadoCBO", False))

        ficha = ClassificacaoAtletaCategoria(
            cbo=cbo,
            nome=nome,
            clubeId=clubeId,
            clubeSigla=clubeSigla,
            clubeNome=clubeNome,
            clubeFiliadoCBO=clubeFiliado,
            categoria=categoria,
        )

        # Primeiro passo: pontos brutos das etapas em que não foi voluntário
        for etapaNum in numerosEtapas:
            regEtapa = mapaEtapas.get(etapaNum)
            ehVol = (etapaNum, cbo) in voluntariosSet
            penalizado23 = (etapaNum, cbo) in penalidadesArt23Set

            if ehVol:
                ficha.etapas[etapaNum] = DesempenhoEtapaCalculado(
                    etapa=etapaNum,
                    inscrito=regEtapa is not None,
                    participou=True,
                    atuouComoVoluntario=True,
                    statusCodigo=regEtapa["statusCodigo"] if regEtapa else None,
                    statusSigla="VOL",
                    tempo=None,
                    colocacao=None,
                    pontosBrutos=Decimal('0.00'),
                    pontosFinais=Decimal('0.00'),
                    passivelDescarte=not penalizado23,
                )
            elif regEtapa is not None:
                stCod = int(regEtapa["statusCodigo"])
                coloc = colocacoesNaEtapa.get((etapaNum, categoria, cbo))
                pts = calcularPontosStatusHelga(
                    categoria=categoria,
                    statusCodigo=stCod,
                    colocacao=coloc,
                    percursoAnulado=False,
                    regras=regras,
                )
                participouNaPista = stCod in (STATUS_OK,) or stCod in STATUS_NAO_CLASSIFICADO_COM_PONTO
                ficha.etapas[etapaNum] = DesempenhoEtapaCalculado(
                    etapa=etapaNum,
                    inscrito=True,
                    participou=participouNaPista,
                    atuouComoVoluntario=False,
                    statusCodigo=stCod,
                    statusSigla=regEtapa["statusSigla"],
                    tempo=regEtapa["tempo"] if stCod != STATUS_NP else None,
                    colocacao=coloc,
                    pontosBrutos=Decimal(pts),
                    pontosFinais=Decimal(pts),
                    passivelDescarte=not penalizado23,
                )
            else:
                ficha.etapas[etapaNum] = DesempenhoEtapaCalculado(
                    etapa=etapaNum,
                    inscrito=False,
                    participou=False,
                    atuouComoVoluntario=False,
                    statusCodigo=None,
                    statusSigla="-",
                    tempo=None,
                    colocacao=None,
                    pontosBrutos=Decimal('0.00'),
                    pontosFinais=Decimal('0.00'),
                    passivelDescarte=True,
                )

        # Contagem de etapas participadas (competiu na pista ou atuou como voluntário convocado)
        etapasComParticipacao = sum(1 for d in ficha.etapas.values() if d.participou)
        ficha.etapasParticipadas = etapasComParticipacao
        ficha.elegivelPremiacao = (
            atletaFiliadoCBO(cbo)
            and etapasComParticipacao >= minimoEtapasPremiacaoEVoluntario
            and not ehCategoriaSemPontuacao(categoria)
        )

        # Etapas que contam para o mínimo exigido ao voluntário: 2026 "participar" (inclui a etapa de apoio);
        # 2025 "competir" (só etapas em que o atleta largou, sem a de voluntário/árbitro).
        if regras.voluntarioContaEtapaDeApoioNoMinimo:
            etapasContadasParaVoluntario = etapasComParticipacao
        else:
            etapasContadasParaVoluntario = sum(
                1 for d in ficha.etapas.values() if d.participou and not d.atuouComoVoluntario
            )

        # Segundo passo: calcular média de voluntário (2026 Art. 33, § 1º; 2025 Art. 36) quando atuou como voluntário
        for etapaNum, des in ficha.etapas.items():
            if not des.atuouComoVoluntario or ehCategoriaSemPontuacao(categoria):
                continue
            if regras.mediaVoluntarioDivideEntre == "todasAsOutras":
                # 2025: todas as outras etapas realizadas; sem inscrição ou de apoio entram com 0 ponto.
                outrasInscritas = [
                    (Decimal('0.00') if d.atuouComoVoluntario else d.pontosBrutos, d.passivelDescarte)
                    for et, d in sorted(ficha.etapas.items())
                    if et != etapaNum
                ]
            else:
                outrasInscritas = [
                    (d.pontosBrutos, d.passivelDescarte)
                    for et, d in sorted(ficha.etapas.items())
                    if et != etapaNum and d.inscrito and not d.atuouComoVoluntario
                ]
            mediaVol = calcularMediaVoluntarioCCO(
                etapasRealizadasNoCampeonato=totalEtapasRealizadas,
                resultadosInscritosExcetoVoluntario=outrasInscritas,
                participouEtapasTotais=etapasContadasParaVoluntario,
                regras=regras,
            )
            des.pontosBrutos = mediaVol
            des.pontosFinais = mediaVol
            des.direitoMediaVoluntario = mediaVol > Decimal('0.00')

        # Ajustes do resultado oficial publicado: substituem a nota da etapa já calculada (ADR-007)
        for etapaAj in numerosEtapas:
            chaveAj = (etapaAj, cbo, categoria)
            if chaveAj in ajustesOficiais:
                desAj = ficha.etapas[etapaAj]
                desAj.pontosBrutos = desAj.pontosFinais = ajustesOficiais[chaveAj]
                desAj.ajustadoOficial = True
                desAj.destaqueMedia = chaveAj in ajustesComDestaqueMedia
                ajustesAplicados.add(chaveAj)

        # Terceiro passo: aplicar o descarte obrigatório (2026, Art. 34, se > 3 etapas); 2025 não tem descarte
        if descarteAplicado and not ehCategoriaSemPontuacao(categoria):
            sequenciaNotas = [
                (ficha.etapas[et].pontosFinais, ficha.etapas[et].passivelDescarte)
                for et in numerosEtapas
            ]
            idxDesc = selecionarIndiceDescarte(sequenciaNotas)
            if idxDesc is not None:
                etapaDesc = numerosEtapas[idxDesc]
                ficha.etapaDescartada = etapaDesc
                ficha.etapas[etapaDesc].descartada = True

        ficha.pontuacaoTotal = arredondarPontuacao(
            sum(
                (d.pontosFinais for d in ficha.etapas.values() if not d.descartada),
                Decimal('0.00'),
            )
        )
        fichasPorAtletaCat.append(ficha)

    omitidas: set[tuple[int, str]] = set()
    mantidas: list[ClassificacaoAtletaCategoria] = []
    for f in fichasPorAtletaCat:
        if (f.cbo, f.categoria) in omissoesOficiais:
            if f.pontuacaoTotal != 0:
                raise ValueError(f"omissão oficial de atleta com pontos: CBO {f.cbo}, {f.categoria}")
            omitidas.add((f.cbo, f.categoria))
        else:
            mantidas.append(f)
    if omissoesOficiais - omitidas:
        raise ValueError(
            "omissões oficiais sem ficha correspondente (CBO, categoria): "
            + "; ".join(f"CBO {c}, {k}" for c, k in sorted(omissoesOficiais - omitidas, key=str))
        )
    fichasPorAtletaCat = mantidas

    semFicha = sorted(set(ajustesOficiais) - ajustesAplicados)
    if semFicha:
        raise ValueError(
            "ajustes oficiais sem ficha correspondente (etapa, CBO, categoria): "
            + "; ".join(f"{e}ª etapa, CBO {c}, {k}" for e, c, k in semFicha)
        )

    # 4. Regra de troca de categoria (Art. 32): pontuação não acumula; vale a de melhor resultado (ou mais recente)
    porAtleta: dict[int, list[ClassificacaoAtletaCategoria]] = {}
    porNomeNormalizado: dict[str, list[ClassificacaoAtletaCategoria]] = {}
    for f in fichasPorAtletaCat:
        porAtleta.setdefault(f.cbo, []).append(f)
        if not ehCategoriaSemPontuacao(f.categoria):
            porNomeNormalizado.setdefault(f.nome.strip().upper(), []).append(f)

    for listaFichas in porAtleta.values():
        fichasCompetitivas = [f for f in listaFichas if not ehCategoriaSemPontuacao(f.categoria)]
        if len(fichasCompetitivas) > 1:
            for f in fichasCompetitivas:
                f.competiuEmMultiplasCategorias = True
        if len(listaFichas) <= 1:
            continue

        def chaveMelhorCategoria(f: ClassificacaoAtletaCategoria) -> tuple[Decimal, int]:
            ultimaEtapaComInscricao = max(
                (et for et, d in f.etapas.items() if d.inscrito),
                default=0,
            )
            return (f.pontuacaoTotal, ultimaEtapaComInscricao)

        melhor = max(listaFichas, key=chaveMelhorCategoria)
        for f in listaFichas:
            f.categoriaValidaFinal = (f is melhor)

    for _, listaMesmoNome in porNomeNormalizado.items():
        if len(listaMesmoNome) > 1:
            for f in listaMesmoNome:
                f.competiuEmMultiplasCategorias = True

    # 5. Ordenar classificação individual por categoria e aplicar o desempate do regulamento do ano.
    # 2026, Art. 34, § 2º: melhor resultado no último percurso -> percurso anterior sucessivamente.
    # 2025, Art. 38, Parágrafo Único: mais 1ºs lugares, 2ºs... -> último confronto direto.
    # O critério "maior idade" não é aplicado: o ano de nascimento não é extraído (ADR-003).
    # Persistindo o empate, a ficha é sinalizada (empateNaoResolvido) e a ordem segue o CBO.
    fichasPorCategoria: dict[str, list[ClassificacaoAtletaCategoria]] = {}
    for f in fichasPorAtletaCat:
        fichasPorCategoria.setdefault(f.categoria, []).append(f)

    for cat, lista in fichasPorCategoria.items():
        sinalizarEmpates = not ehCategoriaSemPontuacao(cat)
        if regras.desempateIndividual == "primeirosLugares":
            ordenarCategoriaPorPrimeirosLugares(lista, numerosEtapas, sinalizarEmpates)
        else:
            ordenarCategoriaPorUltimoPercurso(lista, numerosEtapas, sinalizarEmpates)
        aplicarPosicoesOficiais(lista, cat, posicoesOficiais, posicoesAplicadas)
        posFinal = 1
        for idxCat, f in enumerate(lista, start=1):
            f.colocacaoNaCategoria = idxCat
            if f.categoriaValidaFinal and not ehCategoriaSemPontuacao(cat) and f.pontuacaoTotal > 0:
                f.colocacaoFinal = posFinal
                posFinal += 1
            else:
                f.colocacaoFinal = 0

    semPosicao = sorted(set(posicoesOficiais) - posicoesAplicadas)
    if semPosicao:
        raise ValueError(
            "posições oficiais sem ficha correspondente (CBO, categoria): "
            + "; ".join(f"CBO {c}, {k}" for c, k in semPosicao)
        )

    # 6. Calcular pontuação de clubes por etapa e geral (Art. 35 e Parágrafo Único)
    clubesInfo = {int(c["clubeId"]): c for c in dadosHelga["clubes"]}
    resultadoClubes: dict[int, dict[str, Any]] = {}
    for clubeId, cInfo in clubesInfo.items():
        if not cInfo.get("filiadoCBO", False):
            continue
        if regras.federacaoExigidaDoClube and cInfo.get("federacaoSigla") != regras.federacaoExigidaDoClube:
            continue
        resultadoClubes[clubeId] = {
            "clubeId": clubeId,
            "sigla": cInfo["sigla"],
            "nome": cInfo["nome"],
            "federacaoSigla": cInfo.get("federacaoSigla"),
            "atletasFiliadosParticipantes": set(),
            "pontosPorEtapa": {et: Decimal('0.00') for et in numerosEtapas},
            "detalheTop3PorEtapa": {et: {} for et in numerosEtapas},
            "contagemColocacoes": {pos: 0 for pos in range(1, 50)},
            "totalPontos": Decimal('0.00'),
        }

    for f in fichasPorAtletaCat:
        if f.clubeId not in resultadoClubes:
            continue
        ehFiliado = atletaFiliadoCBO(f.cbo)
        clubeAcum = resultadoClubes[f.clubeId]
        for et in numerosEtapas:
            des = f.etapas[et]
            if des.participou and ehFiliado:
                clubeAcum["atletasFiliadosParticipantes"].add(f.cbo)
            if ehFiliado and des.colocacao is not None and des.colocacao >= 1:
                clubeAcum["contagemColocacoes"][des.colocacao] = (
                    clubeAcum["contagemColocacoes"].get(des.colocacao, 0) + 1
                )

    for et in numerosEtapas:
        for clubeId, clubeAcum in resultadoClubes.items():
            porCatNoClube: dict[str, list[tuple[Decimal, int, str]]] = {}
            for f in fichasPorAtletaCat:
                if f.clubeId != clubeId or ehCategoriaSemPontuacao(f.categoria):
                    continue
                des = f.etapas[et]
                if atletaFiliadoCBO(f.cbo) and des.pontosFinais > 0:
                    porCatNoClube.setdefault(f.categoria, []).append(
                        (des.pontosFinais, f.cbo, f.nome)
                    )
            somaEtapa = Decimal('0.00')
            for cat, candidatos in sorted(porCatNoClube.items()):
                candidatos.sort(key=lambda item: item[0], reverse=True)
                top3 = candidatos[:3]
                somaCat = sum((item[0] for item in top3), Decimal('0.00'))
                somaEtapa += somaCat
                clubeAcum["detalheTop3PorEtapa"][et][cat] = [
                    {"cbo": cbo, "nome": nome, "pontos": str(pts)}
                    for pts, cbo, nome in top3
                ]
            clubeAcum["pontosPorEtapa"][et] = arredondarPontuacao(somaEtapa)

    listaClubesOrdenada = list(resultadoClubes.values())
    for c in listaClubesOrdenada:
        c["totalPontos"] = arredondarPontuacao(sum(c["pontosPorEtapa"].values(), Decimal('0.00')))
        c["qtdAtletas"] = len(c["atletasFiliadosParticipantes"])

    # Art. 35, Parágrafo Único: desempate por mais 1ºs lugares, depois 2ºs, sucessivamente
    listaClubesOrdenada.sort(
        key=lambda c: (
            c["totalPontos"],
            tuple(c["contagemColocacoes"].get(pos, 0) for pos in range(1, 30)),
        ),
        reverse=True,
    )

    etapasComVoluntarios = sorted({
        int(v["etapa"])
        for v in dadosVoluntarios.get("voluntarios", [])
        if v.get("funcao", "voluntario") != "arbitro"
    })
    etapasComArbitros = sorted({
        int(v["etapa"])
        for v in dadosVoluntarios.get("voluntarios", [])
        if v.get("funcao") == "arbitro"
    })

    return {
        "regras": regras,
        "descarteAplicado": descarteAplicado,
        "minimoMetadeEtapas": minimoEtapasPremiacaoEVoluntario,
        "etapas": etapasInfo,
        "ajustesOficiais": [
            {"etapa": e, "cbo": c, "categoria": k, "pontos": str(p)} for (e, c, k), p in sorted(ajustesOficiais.items())
        ],
        "omissoesOficiais": sorted(
            ({"categoria": k, "cbo": c} for c, k in omissoesOficiais), key=lambda o: (o["categoria"], o["cbo"])
        ),
        "posicoesOficiais": [
            {"categoria": k, "cbo": c, "posicao": p} for (c, k), p in sorted(posicoesOficiais.items(), key=str)
        ],
        "etapasComVoluntarios": etapasComVoluntarios,
        "etapasComArbitros": etapasComArbitros,
        "fichasPorCategoria": fichasPorCategoria,
        "classificacaoClubes": listaClubesOrdenada,
    }
