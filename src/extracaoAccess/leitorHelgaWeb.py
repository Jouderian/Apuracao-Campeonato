# -*- coding: utf-8 -*-
"""Leitura da planilha exportada do site de resultados do Helga (HelgaO WebRes).

Gera o JSON complementar `etapasHelgaWeb<ano>.json`, no mesmo esquema do JSON extraído do banco, a partir
da lista de partida (todos os inscritos) e do resultado de cada etapa. Ver a spec web-results-ingestion
e o ADR-006. Nada é corrigido por estimativa: qualquer inconsistência recusa a extração.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter
from typing import Any

from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.extracaoAccess.inspecionarBanco import calcularSha256  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    NOME_MANIFESTO,
    EntradaInvalidaError,
    lerManifestoSha256,
    validarDadosHelga,
)

NOME_PLANILHA = "exportadoSiteHelga.xlsx"
PREFIXOS_CATEGORIAS_FORA_DO_CCO: tuple[str, ...] = ("Militar",)

# Códigos de status do Helga (tabela Status do banco).
STATUS_OK, STATUS_NC, STATUS_NP, STATUS_OT = (0, "OK"), (1, "NC"), (3, "NP"), (5, "OT")
STATUS_DA_COLOCACAO: dict[str, tuple[int, str]] = {"NCL": STATUS_NC, "OT": STATUS_OT, "ACT": STATUS_OK}

RE_CABECALHO_RESULTADO = re.compile(r"^(?P<cat>.+?)\s*\((?P<n>\d+)\)\s*length\s*(?P<comp>\d+)\s*m")
RE_CABECALHO_CLUBE = re.compile(r"^(?P<clube>.+?)\s*\((?P<n>\d+)\)$")
RE_COLOCACAO = re.compile(r"^(\d+)\.$")
RE_MINKM = re.compile(r"^(\d+)'(\d{2})\"?$")
RE_ABA = re.compile(r"^(listaPartida|resultado)Etapa(\d+)$")


def _limpar(valor: Any) -> str:
    """Normaliza espaços (inclusive o espaço não separável que o site grava) e apara as pontas."""
    return re.sub(r"\s+", " ", str(valor if valor is not None else "").replace("\xa0", " ")).strip()


def _celula(linha: tuple[Any, ...], indice: int) -> Any:
    return linha[indice] if indice < len(linha) else None


def _segundosDeTexto(texto: str) -> int:
    partes = [int(p) for p in texto.lstrip("+").split(":")]
    return partes[0] * 3600 + partes[1] * 60 + partes[2] if len(partes) == 3 else partes[0] * 60 + partes[1]


def formatarTempo(segundos: int) -> str:
    """Formata segundos como `HH:MM:SS`, o mesmo formato do JSON extraído do banco."""
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"


def _leiturasDoTempo(celula: Any) -> dict[str, int]:
    """Duas leituras possíveis da célula de tempo.

    `mmss`: a página mostrava `mm:ss` e o Excel guardou o minuto como hora e o segundo como minuto.
    `hmmss`: a página mostrava `h:mm:ss`. Só existe `mmss` quando o campo de segundos da célula é zero.
    """
    if isinstance(celula, dt.timedelta):
        horas, minutos, segundos = celula.days * 24 + celula.seconds // 3600, celula.seconds % 3600 // 60, celula.seconds % 60
    elif isinstance(celula, dt.time):
        horas, minutos, segundos = celula.hour, celula.minute, celula.second
    else:
        return {}
    leituras = {"hmmss": horas * 3600 + minutos * 60 + segundos}
    if segundos == 0:
        leituras["mmss"] = horas * 60 + minutos
    return leituras


def resolverTempoSegundos(celula: Any, minKm: Any, comprimentoMetros: int) -> int | None:
    """Escolhe a leitura do tempo compatível com min/km × distância; `None` se não houver uma só."""
    leituras = _leiturasDoTempo(celula)
    m = RE_MINKM.match(_limpar(minKm))
    if not leituras or not m:
        return None
    alvo = (int(m.group(1)) * 60 + int(m.group(2))) * comprimentoMetros / 1000
    tolerancia = 1.5 + comprimentoMetros / 1000 * 0.5   # min/km é arredondado ao segundo
    compativeis = [v for v in leituras.values() if abs(v - alvo) <= tolerancia]
    return compativeis[0] if len(compativeis) == 1 else None


def lerListaPartida(linhas: list[tuple[Any, ...]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Lê a aba de lista de partida (blocos por clube); devolve os inscritos e os problemas."""
    inscritos: list[dict[str, Any]] = []
    problemas: list[str] = []
    clube, esperado, lidos = "", 0, 0

    def fecharBloco() -> None:
        if clube and lidos != esperado:
            problemas.append(f"lista de partida, {clube}: cabeçalho diz {esperado}, lidos {lidos}")

    for linha in linhas:
        primeira = _celula(linha, 0)
        if isinstance(primeira, str):
            m = RE_CABECALHO_CLUBE.match(_limpar(primeira))
            if not m:
                problemas.append(f"lista de partida: cabeçalho de clube não entendido: {primeira!r}")
                continue
            fecharBloco()
            clube, esperado, lidos = _limpar(m.group("clube")), int(m.group("n")), 0
        elif isinstance(primeira, int) and not isinstance(primeira, bool):
            codigo = re.sub(r"\D", "", str(_celula(linha, 4) or ""))
            inscritos.append({
                "cbo": primeira, "nome": _limpar(_celula(linha, 2)), "runnerPk": int(codigo) if codigo else 0,
                "categoria": _limpar(_celula(linha, 6)), "clubeNome": clube,
            })
            lidos += 1
    fecharBloco()
    return inscritos, problemas


def lerResultados(linhas: list[tuple[Any, ...]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Lê a aba de resultado (blocos por categoria); devolve as linhas e os problemas."""
    resultados: list[dict[str, Any]] = []
    problemas: list[str] = []
    categoria, esperado, comprimento, lidos = "", 0, 0, 0

    def fecharBloco() -> None:
        if categoria and lidos != esperado:
            problemas.append(f"resultado, {categoria}: cabeçalho diz {esperado}, lidos {lidos}")

    for linha in linhas:
        primeira = _celula(linha, 0)
        if isinstance(primeira, str) and "length" in primeira:
            m = RE_CABECALHO_RESULTADO.match(_limpar(primeira))
            if not m:
                problemas.append(f"resultado: cabeçalho de categoria não entendido: {primeira!r}")
                continue
            fecharBloco()
            categoria, esperado, comprimento, lidos = _limpar(m.group("cat")), int(m.group("n")), int(m.group("comp")), 0
            continue
        if not isinstance(primeira, str) or _celula(linha, 6) == "[H:]M:S":
            continue
        colocacao = _limpar(primeira)
        if not RE_COLOCACAO.match(colocacao) and colocacao not in STATUS_DA_COLOCACAO:
            problemas.append(f"resultado, {categoria}: situação desconhecida {colocacao!r}")
            continue
        lidos += 1
        resultados.append({
            "categoria": categoria, "comprimento": comprimento, "colocacao": colocacao,
            "cbo": _celula(linha, 3), "nome": _limpar(_celula(linha, 2)), "tempoCelula": _celula(linha, 6),
            "minKm": _celula(linha, 7), "diferenca": _limpar(_celula(linha, 8)),
        })
    fecharBloco()
    return resultados, problemas


def _foraDoCco(categoria: str) -> bool:
    return categoria.startswith(PREFIXOS_CATEGORIAS_FORA_DO_CCO)


def _validarResultadosDaCategoria(categoria: str, linhas: list[dict[str, Any]], avisos: list[str]) -> list[str]:
    """Confere colocação, tempo (min/km) e diferença para o líder; preenche `segundos` nas linhas."""
    problemas: list[str] = []
    classificados = [r for r in linhas if RE_COLOCACAO.match(r["colocacao"])]
    for posicao, r in enumerate(classificados, 1):
        if int(r["colocacao"][:-1]) != posicao:
            problemas.append(f"{categoria}: colocação {r['colocacao']} na posição {posicao} (CBO {r['cbo']})")
    for r in linhas:
        r["segundos"] = None
        if r["colocacao"] == "ACT" or not RE_COLOCACAO.match(r["colocacao"]):
            continue
        r["segundos"] = resolverTempoSegundos(r["tempoCelula"], r["minKm"], r["comprimento"])
        if r["segundos"] is None:
            problemas.append(
                f"{categoria}: CBO {r['cbo']} tempo {r['tempoCelula']!r} sem leitura única compatível com "
                f"min/km {r['minKm']!r} e {r['comprimento']} m"
            )
    segundos = [r["segundos"] for r in classificados]
    if None not in segundos:
        if segundos != sorted(segundos):
            problemas.append(f"{categoria}: tempos fora de ordem")
        for r in classificados[1:]:
            if r["diferenca"] and r["segundos"] - segundos[0] != _segundosDeTexto(r["diferenca"]):
                problemas.append(
                    f"{categoria}: CBO {r['cbo']} tempo - líder = {r['segundos'] - segundos[0]} s, "
                    f"diferença do site +{r['diferenca']}"
                )
        for anterior, atual in zip(classificados, classificados[1:], strict=False):
            if anterior["segundos"] == atual["segundos"]:
                avisos.append(
                    f"{categoria}: CBO {anterior['cbo']} e {atual['cbo']} com o mesmo tempo "
                    f"({formatarTempo(atual['segundos'])}); vale a colocação do site"
                )
    return problemas


def montarRegistrosEtapa(
    numeroEtapa: int,
    competitionId: int,
    inscritos: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
    clubesPorNome: dict[str, dict[str, Any]],
    categoriaIdPorNome: dict[str, int],
    avisos: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Cruza lista de partida e resultado e devolve os registros da etapa (no formato do JSON do banco)."""
    problemas: list[str] = []
    inscritos = [i for i in inscritos if not _foraDoCco(i["categoria"])]
    resultados = [r for r in resultados if not _foraDoCco(r["categoria"])]

    chaves = Counter((i["cbo"], i["categoria"]) for i in inscritos)
    problemas += [f"lista de partida: CBO {c} repetido na categoria {k}" for (c, k), n in chaves.items() if n > 1]
    porChave = {(i["cbo"], i["categoria"]): i for i in inscritos}

    resultadoPorChave: dict[tuple[int, str], dict[str, Any]] = {}
    porCategoria: dict[str, list[dict[str, Any]]] = {}
    for r in resultados:
        porCategoria.setdefault(r["categoria"], []).append(r)
    for categoria, linhas in porCategoria.items():
        problemas += _validarResultadosDaCategoria(categoria, linhas, avisos)
        for r in linhas:
            chave = (r["cbo"], categoria)
            if chave not in porChave:
                problemas.append(f"resultado de {r['nome']} (CBO {r['cbo']}, {categoria}) ausente da lista de partida")
            else:
                resultadoPorChave[chave] = r

    registros: list[dict[str, Any]] = []
    for chave, inscrito in porChave.items():
        clube = clubesPorNome.get(inscrito["clubeNome"])
        if clube is None:
            problemas.append(f"clube da lista de partida ausente da tabela de clubes do banco: {inscrito['clubeNome']!r}")
            continue
        resultado = resultadoPorChave.get(chave)
        if resultado is None:
            (codigo, sigla), tempo, segundos = STATUS_NP, None, None
        else:
            (codigo, sigla) = STATUS_DA_COLOCACAO.get(resultado["colocacao"], STATUS_OK)
            segundos = resultado["segundos"]
            tempo = formatarTempo(segundos) if segundos is not None else None
        registros.append({
            "competitionId": competitionId, "runnerPk": inscrito["runnerPk"], "cbo": inscrito["cbo"],
            "nome": inscrito["nome"], "sexo": 2 if inscrito["categoria"].startswith("D") else 1,
            "clubeId": clube["clubeId"], "clubeSigla": clube["sigla"], "clubeNome": clube["nome"],
            "clubeFiliadoCBO": bool(clube.get("filiadoCBO", False)),
            "categoriaId": categoriaIdPorNome.get(inscrito["categoria"], 0), "categoria": inscrito["categoria"],
            "statusCodigo": codigo, "statusSigla": sigla, "classifyYN": resultado is None or resultado["colocacao"] != "ACT",
            "tempo": tempo, "tempoSegundos": segundos, "tempoMs": 0, "etapa": numeroEtapa,
        })
    return registros, problemas


def extrairComplemento(
    caminhoXlsx: str,
    ano: int,
    base: dict[str, Any],
    etapasNovas: dict[int, dict[str, Any]],
    sha256: str,
    aliasClubes: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Monta o JSON complementar a partir da planilha; levanta `EntradaInvalidaError` listando os problemas."""
    wb = load_workbook(caminhoXlsx, data_only=True, read_only=True)
    abas: dict[tuple[str, int], list[tuple[Any, ...]]] = {}
    for nome in wb.sheetnames:
        m = RE_ABA.match(nome)
        if m:
            abas[(m.group(1), int(m.group(2)))] = [tuple(linha) for linha in wb[nome].iter_rows(values_only=True)]
    wb.close()
    numeros = sorted({n for _, n in abas})
    if not numeros:
        raise EntradaInvalidaError("planilha sem abas listaPartidaEtapa<N> e resultadoEtapa<N>")

    clubesPorNome = {_limpar(c["nome"]): c for c in base["clubes"]}
    problemas: list[str] = []
    clubesPorSigla = {c["sigla"]: c for c in base["clubes"]}
    for nomeNoSite, sigla in (aliasClubes or {}).items():
        if sigla in clubesPorSigla:
            clubesPorNome[_limpar(nomeNoSite)] = clubesPorSigla[sigla]
        else:
            problemas.append(f"--alias-clube: sigla {sigla!r} ausente da tabela de clubes do banco")
    categoriaIdPorNome = {r["categoria"]: r["categoriaId"] for r in base["registrosEtapas"]}
    etapasBase = {e["numeroEtapa"]: e for e in base["etapas"]}
    perfisBase = base["perfisAtletas"]

    avisos: list[str] = []
    etapas: list[dict[str, Any]] = []
    registros: list[dict[str, Any]] = []
    for n in numeros:
        if ("listaPartida", n) not in abas or ("resultado", n) not in abas:
            problemas.append(f"etapa {n}: faltam a aba de lista de partida ou a de resultado")
            continue
        if n in etapasBase:
            etapa = dict(etapasBase[n])
        elif n in etapasNovas:
            etapa = dict(etapasNovas[n])
        else:
            problemas.append(f"etapa {n} não existe no banco: informe os metadados com --etapa-nova")
            continue
        inscritos, p1 = lerListaPartida(abas[("listaPartida", n)])
        resultados, p2 = lerResultados(abas[("resultado", n)])
        problemas += [f"etapa {n}: {p}" for p in p1 + p2]
        regs, p3 = montarRegistrosEtapa(
            n, int(etapa["competitionId"]), inscritos, resultados, clubesPorNome, categoriaIdPorNome, avisos,
        )
        problemas += [f"etapa {n}: {p}" for p in p3]
        etapas.append(etapa)
        registros += regs
    if problemas:
        resumo = problemas[:40] + ([f"... e mais {len(problemas) - 40} problema(s)"] if len(problemas) > 40 else [])
        raise EntradaInvalidaError("; ".join(resumo))

    perfis: dict[str, dict[str, Any]] = {}
    for r in registros:
        chave = str(r["cbo"])
        if chave not in perfisBase and chave not in perfis:
            perfis[chave] = {
                "cbo": r["cbo"], "nome": r["nome"], "sexo": r["sexo"], "clubeId": r["clubeId"],
                "clubeSigla": r["clubeSigla"], "clubeNome": r["clubeNome"],
                "clubeFiliadoCBO": r["clubeFiliadoCBO"], "categoriaPadrao": r["categoria"],
            }
    idsClubes = {r["clubeId"] for r in registros}
    complemento = {
        "fonte": os.path.basename(caminhoXlsx),
        "sha256Fonte": sha256,
        "etapas": etapas,
        "clubes": [c for c in base["clubes"] if c["clubeId"] in idsClubes],
        "perfisAtletas": perfis,
        "registrosEtapas": registros,
    }
    validarDadosHelga(complemento)
    return complemento, avisos


def registrarNoManifesto(pastaDados: str, ano: int, nomeArquivo: str, sha256: str) -> str:
    """Congela o arquivo no manifesto; recusa hash diferente do já registrado. Devolve `novo` ou `ja registrado`."""
    caminho = os.path.join(pastaDados, NOME_MANIFESTO)
    chave = f"{ano}/{nomeArquivo}"
    existente = lerManifestoSha256(caminho).get(chave)
    if existente == sha256:
        return "já registrado"
    if existente is not None:
        raise EntradaInvalidaError(
            f"{chave} já está congelado com outro SHA-256 ({existente}); arquivo congelado não pode mudar"
        )
    with open(caminho, encoding="utf-8") as fh:
        conteudo = fh.read()
    with open(caminho, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(("" if conteudo.endswith("\n") else "\n") + f"{sha256}  {chave}\n")
    return "novo"


def _lerEtapaNova(texto: str) -> tuple[int, dict[str, Any]]:
    """Lê `NUM|AAAA-MM-DD|SIGLA_CLUBE|LOCAL|COMPETITION_ID` (etapa sem banco)."""
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) != 5 or not partes[0].isdigit() or not partes[4].isdigit():
        raise ValueError(f"--etapa-nova inválido: {texto!r} (esperado NUM|AAAA-MM-DD|SIGLA_CLUBE|LOCAL|COMPETITION_ID)")
    dt.date.fromisoformat(partes[1])
    return int(partes[0]), {
        "numeroEtapa": int(partes[0]), "competitionId": int(partes[4]), "data": partes[1],
        "local": partes[3], "clubeOrganizadorSigla": partes[2],
    }


def _lerAlias(texto: str) -> tuple[str, str]:
    """Lê `NOME NO SITE=SIGLA` (mesmo clube grafado de outro modo no site)."""
    nome, separador, sigla = texto.rpartition("=")
    if not separador or not nome.strip() or not sigla.strip():
        raise ValueError(f"--alias-clube inválido: {texto!r} (esperado NOME NO SITE=SIGLA)")
    return nome.strip(), sigla.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera o JSON complementar de um ano a partir da planilha exportada do site de resultados do Helga."
    )
    parser.add_argument("--ano", type=int, required=True, help="Ano da edição (ex.: 2025)")
    parser.add_argument("--etapa-nova", action="append", default=[], metavar="NUM|DATA|SIGLA_CLUBE|LOCAL|COMPETITION_ID",
                        help="Metadados de etapa que não existe no banco (repetível)")
    parser.add_argument("--alias-clube", action="append", default=[], metavar="NOME NO SITE=SIGLA",
                        help="Clube grafado no site de outro modo que no banco (repetível)")
    args = parser.parse_args()

    raiz = RAIZ
    pastaDados = os.path.join(raiz, "Dados")
    pastaAno = os.path.join(pastaDados, str(args.ano))
    caminhoXlsx = os.path.join(pastaAno, "entradas", NOME_PLANILHA)
    caminhoBase = os.path.join(pastaAno, "extraidos", f"etapasHelga{args.ano}.json")
    caminhoSaida = os.path.join(pastaAno, "extraidos", f"etapasHelgaWeb{args.ano}.json")
    for caminho in (caminhoXlsx, caminhoBase):
        if not os.path.isfile(caminho):
            print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
            return 1
    try:
        etapasNovas = dict(_lerEtapaNova(t) for t in args.etapa_nova)
        with open(caminhoBase, encoding="utf-8") as fh:
            base = json.load(fh)
        sha256 = calcularSha256(caminhoXlsx)
        alias = dict(_lerAlias(t) for t in args.alias_clube)
        complemento, avisos = extrairComplemento(caminhoXlsx, args.ano, base, etapasNovas, sha256, alias)
        situacao = registrarNoManifesto(pastaDados, args.ano, NOME_PLANILHA, sha256)
    except (ValueError, OSError) as erro:
        print(f"Extração recusada: {erro}", file=sys.stderr)
        return 1

    with open(caminhoSaida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(complemento, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)
    contagem = Counter((r["etapa"], r["statusSigla"]) for r in complemento["registrosEtapas"])
    print(f"Complemento gerado: {os.path.relpath(caminhoSaida, raiz)} (SHA-256 {situacao} no manifesto)")
    for etapa in complemento["etapas"]:
        n = etapa["numeroEtapa"]
        situacoes = ", ".join(f"{s}={q}" for (e, s), q in sorted(contagem.items()) if e == n)
        print(f"  - {n}ª etapa: {situacoes}")
    print(f"  - atletas novos no cadastro: {len(complemento['perfisAtletas'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
