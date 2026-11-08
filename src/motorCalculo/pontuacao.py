# -*- coding: utf-8 -*-
"""Regras puras de pontuação e apuração do Campeonato Cearense de Orientação (CCO e CCOS).

Implementa os dispositivos do Capítulo 8 (Da Pontuação e Apuração do Campeonato, Arts. 31 a 35),
Art. 23, Parágrafo Único e Art. 39, § 1º do Regulamento das Competições Cearenses de Orientação (2026).
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Sequence

TABELA_PONTOS_COLOCACAO: tuple[int, ...] = (
    40, 37, 35, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24,
    23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11,
)

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


@dataclass
class ClassificacaoAtletaCategoria:
    """Resultado consolidado de um atleta em uma categoria no campeonato."""
    cbo: int
    nome: str
    clubeId: int
    clubeSigla: str
    clubeNome: str
    clubeFiliadoCBO: bool
    anoNascimento: int | None
    categoria: str
    etapas: dict[int, DesempenhoEtapaCalculado] = field(default_factory=dict)
    etapaDescartada: int | None = None
    pontuacaoTotal: Decimal = Decimal('0.00')
    etapasParticipadas: int = 0
    elegivelPremiacao: bool = False
    colocacaoFinal: int = 0
    categoriaValidaFinal: bool = True


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
) -> int:
    """Calcula a pontuação individual em uma etapa/percurso (Regulamento 2026, Art. 31 e ROP 21.5.1).

    - Categorias Acompanhado e percurso aberto: 0 pontos (Art. 31, § 3º).
    - Percurso anulado ou atleta não classificado que participou (NC, OT, DNF, DC): 1 ponto (Art. 31, § 2º).
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


def calcularPontosStatusHelga(
    categoria: str,
    statusCodigo: int,
    colocacao: int | None,
    percursoAnulado: bool = False,
) -> int:
    """Traduz o Status_FK do Helga para a pontuação da etapa segundo o Art. 31 do Regulamento 2026."""
    if statusCodigo in STATUS_SEM_PARTICIPACAO:
        return 0
    if statusCodigo == STATUS_OK:
        return calcularPontosEtapa(
            categoria=categoria,
            concluiuPercurso=True,
            colocacao=colocacao,
            percursoAnulado=percursoAnulado,
            participou=True,
        )
    if statusCodigo in STATUS_NAO_CLASSIFICADO_COM_PONTO:
        return calcularPontosEtapa(
            categoria=categoria,
            concluiuPercurso=False,
            colocacao=None,
            percursoAnulado=percursoAnulado,
            participou=True,
        )
    return 0


def temDireitoDescarteCCO(etapasRealizadasNoCampeonato: int) -> bool:
    """Define se há descarte obrigatório de 1 etapa no CCO (Regulamento 2026, Art. 34, caput e § 1º)."""
    return etapasRealizadasNoCampeonato > 3


def exigirMinimoEtapasVoluntarioCCO(etapasRealizadasNoCampeonato: int) -> int:
    """Retorna o mínimo de etapas em que o voluntário precisa participar no CCO (Regulamento 2026, Art. 33, § 1º).

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
    resultadosInscritosExcetoVoluntario: Sequence[tuple[int | Decimal, bool]],
    participouEtapasTotais: int,
) -> Decimal:
    """Calcula a média de pontos do voluntário/árbitro no CCO (Regulamento 2026, Art. 33, § 1º).

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


def apurarCampeonatoCCO(
    dadosHelga: dict[str, Any],
    dadosVoluntarios: dict[str, Any],
) -> dict[str, Any]:
    """Executa a apuração completa do CCO segundo o Regulamento 2026 (Arts. 23, 31 a 35 e 39)."""
    etapasInfo = sorted(dadosHelga["etapas"], key=lambda e: e["numeroEtapa"])
    numerosEtapas = [e["numeroEtapa"] for e in etapasInfo]
    totalEtapasRealizadas = len(numerosEtapas)
    minimoEtapasPremiacaoEVoluntario = exigirMinimoEtapasVoluntarioCCO(totalEtapasRealizadas)

    voluntariosSet: set[tuple[int, int]] = {
        (int(v["etapa"]), int(v["cbo"]))
        for v in dadosVoluntarios.get("voluntarios", [])
    }
    penalidadesArt23Set: set[tuple[int, int]] = {
        (int(p["etapa"]), int(p["cbo"]))
        for p in dadosVoluntarios.get("penalidadesArt23", [])
    }

    perfis = dadosHelga["perfisAtletas"]
    registros = dadosHelga["registrosEtapas"]

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
    for etapaVol, cboVol in sorted(voluntariosSet):
        cats = categoriasDoAtleta.get(cboVol)
        if cats:
            catAlvo = sorted(cats)[0]
        else:
            perfilVol = perfis.get(str(cboVol), {})
            catAlvo = perfilVol.get("categoriaPadrao") or "Sem Categoria"
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
        anoNasc = amostraReg["anoNascimento"] if amostraReg else perfil.get("anoNascimento")

        ficha = ClassificacaoAtletaCategoria(
            cbo=cbo,
            nome=nome,
            clubeId=clubeId,
            clubeSigla=clubeSigla,
            clubeNome=clubeNome,
            clubeFiliadoCBO=clubeFiliado,
            anoNascimento=anoNasc,
            categoria=categoria,
        )

        # Primeiro passo: pontos brutos das etapas em que não foi voluntário
        for etapaNum in numerosEtapas:
            reg = mapaEtapas.get(etapaNum)
            ehVol = (etapaNum, cbo) in voluntariosSet
            penalizado23 = (etapaNum, cbo) in penalidadesArt23Set

            if ehVol:
                ficha.etapas[etapaNum] = DesempenhoEtapaCalculado(
                    etapa=etapaNum,
                    inscrito=reg is not None,
                    participou=True,
                    atuouComoVoluntario=True,
                    statusCodigo=reg["statusCodigo"] if reg else None,
                    statusSigla="VOL",
                    tempo=None,
                    colocacao=None,
                    pontosBrutos=Decimal('0.00'),
                    pontosFinais=Decimal('0.00'),
                    passivelDescarte=not penalizado23,
                )
            elif reg is not None:
                stCod = int(reg["statusCodigo"])
                coloc = colocacoesNaEtapa.get((etapaNum, categoria, cbo))
                pts = calcularPontosStatusHelga(
                    categoria=categoria,
                    statusCodigo=stCod,
                    colocacao=coloc,
                    percursoAnulado=False,
                )
                participouNaPista = stCod in (STATUS_OK,) or stCod in STATUS_NAO_CLASSIFICADO_COM_PONTO
                ficha.etapas[etapaNum] = DesempenhoEtapaCalculado(
                    etapa=etapaNum,
                    inscrito=True,
                    participou=participouNaPista,
                    atuouComoVoluntario=False,
                    statusCodigo=stCod,
                    statusSigla=reg["statusSigla"],
                    tempo=reg["tempo"] if stCod != STATUS_NP else None,
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

        # Segundo passo: calcular média de voluntário (Art. 33, § 1º) quando houver atuação como voluntário
        for etapaNum, des in ficha.etapas.items():
            if not des.atuouComoVoluntario or ehCategoriaSemPontuacao(categoria):
                continue
            outrasInscritas = [
                (d.pontosBrutos, d.passivelDescarte)
                for et, d in sorted(ficha.etapas.items())
                if et != etapaNum and d.inscrito and not d.atuouComoVoluntario
            ]
            mediaVol = calcularMediaVoluntarioCCO(
                etapasRealizadasNoCampeonato=totalEtapasRealizadas,
                resultadosInscritosExcetoVoluntario=outrasInscritas,
                participouEtapasTotais=etapasComParticipacao,
            )
            des.pontosBrutos = mediaVol
            des.pontosFinais = mediaVol
            des.direitoMediaVoluntario = mediaVol > Decimal('0.00')

        # Terceiro passo: aplicar descarte obrigatório do Art. 34 na classificação geral (se > 3 etapas)
        if temDireitoDescarteCCO(totalEtapasRealizadas) and not ehCategoriaSemPontuacao(categoria):
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

    # 4. Regra de troca de categoria (Art. 32): pontuação não acumula; vale a de melhor resultado (ou mais recente)
    porAtleta: dict[int, list[ClassificacaoAtletaCategoria]] = {}
    for f in fichasPorAtletaCat:
        porAtleta.setdefault(f.cbo, []).append(f)

    for cbo, listaFichas in porAtleta.items():
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

    # 5. Ordenar classificação individual por categoria e aplicar desempate (Art. 34, § 2º)
    # Art. 34, § 2º: melhor resultado no último percurso -> percurso anterior sucessivamente -> maior idade (menor anoNascimento)
    fichasPorCategoria: dict[str, list[ClassificacaoAtletaCategoria]] = {}
    for f in fichasPorAtletaCat:
        fichasPorCategoria.setdefault(f.categoria, []).append(f)

    etapasReversas = list(reversed(numerosEtapas))
    for cat, lista in fichasPorCategoria.items():
        def chaveOrdenacaoIndividual(f: ClassificacaoAtletaCategoria) -> tuple[Any, ...]:
            notasReversas = tuple(f.etapas[et].pontosFinais for et in etapasReversas)
            # Maior idade = menor ano de nascimento; se None, fica por último no desempate de idade
            pesoIdade = -(f.anoNascimento if f.anoNascimento and f.anoNascimento > 0 else 9999)
            return (
                1 if f.categoriaValidaFinal else 0,
                f.pontuacaoTotal,
                *notasReversas,
                pesoIdade,
                -f.cbo,
            )

        lista.sort(key=chaveOrdenacaoIndividual, reverse=True)
        posAtual = 1
        for f in lista:
            if f.categoriaValidaFinal and not ehCategoriaSemPontuacao(cat) and f.pontuacaoTotal > 0:
                f.colocacaoFinal = posAtual
                posAtual += 1
            else:
                f.colocacaoFinal = 0

    # 6. Calcular pontuação de clubes por etapa e geral (Art. 35 e Parágrafo Único)
    clubesInfo = {int(c["clubeId"]): c for c in dadosHelga["clubes"]}
    resultadoClubes: dict[int, dict[str, Any]] = {}
    for clubeId, cInfo in clubesInfo.items():
        if not cInfo.get("filiadoCBO", False):
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
        c["totalPontos"] = arredondarPontuacao(
            sum(c["pontosPorEtapa"].values(), Decimal('0.00'))
        )
        c["qtdAtletas"] = len(c["atletasFiliadosParticipantes"])

    # Art. 35, Parágrafo Único: desempate por mais 1ºs lugares, depois 2ºs, sucessivamente
    listaClubesOrdenada.sort(
        key=lambda c: (
            c["totalPontos"],
            tuple(c["contagemColocacoes"].get(pos, 0) for pos in range(1, 30)),
        ),
        reverse=True,
    )

    return {
        "etapas": etapasInfo,
        "fichasPorCategoria": fichasPorCategoria,
        "classificacaoClubes": listaClubesOrdenada,
    }
