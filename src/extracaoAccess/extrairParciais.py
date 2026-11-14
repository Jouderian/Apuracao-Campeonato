#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extrai as parciais por posto de um arquivo Helga (.mdb/.accdb) para JSON em Dados/<ano>/extraidos/.

Camada B da spec analise-desempenho: postos de cada percurso (com a distância do trecho) e as passagens de
quem concluiu, pela última leitura do chip, conferidas contra o tempo oficial. O número do chip nunca vai para o
JSON. Só roda sobre arquivo cujo SHA-256 esteja no manifesto de arquivos congelados.
"""
import argparse
import json
import os
# Uso restrito a um executável fixo, sem shell (ver extrairBrutoViaPowerShellOdbc).
import subprocess  # nosec B404
import sys
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.extracaoAccess.escopoAnalise import ehCategoriaNaoCompetitiva  # noqa: E402
from src.extracaoAccess.extrairHelga import _caminhoPowerShell  # noqa: E402
from src.extracaoAccess.inspecionarBanco import calcularSha256  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosParciais,
)

TOLERANCIA_SOMA_SEGUNDOS = 1


def extrairBrutoViaPowerShellOdbc(caminhoMdb: str) -> dict[str, Any]:
    """Lê Controls, Course, EmitData e EmitData_Details via .NET OdbcConnection, em modo somente leitura."""
    psScript = """
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# O caminho chega por variável de ambiente, nunca interpolado no script (ADR-004).
$dbq = $env:CCO_MDB_CAMINHO
$conn = New-Object System.Data.Odbc.OdbcConnection("Driver={Microsoft Access Driver (*.mdb, *.accdb)};Dbq=$dbq;ReadOnly=1;")
$conn.Open()

function Get-Rows($sql) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $da = New-Object System.Data.Odbc.OdbcDataAdapter($cmd)
    $dt = New-Object System.Data.DataTable
    [void]$da.Fill($dt)
    return $dt.Rows
}

function IntOuNulo($v) {
    if ($v -is [System.DBNull] -or "$v" -eq "") { return $null }
    return [int]$v
}

$etapas = "(SELECT ID FROM Competition WHERE Event_FK >= 2)"

$postos = @()
foreach ($r in (Get-Rows "SELECT Parcours_FK, Number, Order_Number, Distance FROM Controls WHERE Parcours_FK IN (SELECT ID FROM Parcours WHERE Competition_FK IN $etapas) ORDER BY Parcours_FK, Order_Number")) {
    $postos += [ordered]@{
        percursoId = [int]$r.Parcours_FK
        ordem = [int]$r.Order_Number
        codigoPosto = [int]$r.Number
        distanciaM = IntOuNulo $r.Distance
    }
}

$concluintes = @()
foreach ($r in (Get-Rows "SELECT c.Competition_PK, c.Runner_PK, c.Parcours_FK, c.EmitBadge, cat.Name AS CatName, Format(c.CourseTime, 'hh:nn:ss') AS Tempo FROM Course c INNER JOIN Categories cat ON c.Category_FK = cat.ID WHERE c.Competition_PK IN $etapas AND c.Status_FK = 0 ORDER BY c.Competition_PK, c.Runner_PK")) {
    $concluintes += [ordered]@{
        competitionId = [int]$r.Competition_PK
        runnerPk = [int]$r.Runner_PK
        percursoId = IntOuNulo $r.Parcours_FK
        chip = IntOuNulo $r.EmitBadge
        categoria = "$($r.CatName)".Trim()
        tempo = if ($r.Tempo -is [System.DBNull]) { $null } else { "$($r.Tempo)" }
    }
}

$leituras = @()
foreach ($r in (Get-Rows "SELECT id, Competition_FK, BadgeNumber FROM EmitData WHERE Competition_FK IN $etapas ORDER BY id")) {
    $leituras += [ordered]@{
        leituraId = [int]$r.id
        competitionId = [int]$r.Competition_FK
        chip = IntOuNulo $r.BadgeNumber
    }
}

$passagens = @()
foreach ($r in (Get-Rows "SELECT d.EmitData_pk, d.seq, d.control, d.split FROM EmitData_Details d INNER JOIN EmitData e ON d.EmitData_pk = e.id WHERE e.Competition_FK IN $etapas ORDER BY d.EmitData_pk, d.seq")) {
    $seg = $null
    if ($r.split -isnot [System.DBNull]) { $seg = [int][math]::Round(([datetime]$r.split).TimeOfDay.TotalSeconds) }
    $passagens += [ordered]@{
        leituraId = [int]$r.EmitData_pk
        ordem = [int]$r.seq
        codigoPosto = [int]$r.control
        tempoParcialSegundos = $seg
    }
}

$conn.Close()

$out = [ordered]@{
    postos = $postos
    concluintes = $concluintes
    leituras = $leituras
    passagens = $passagens
}
$out | ConvertTo-Json -Depth 5 -Compress
"""
    ambiente = {**os.environ, "CCO_MDB_CAMINHO": os.path.abspath(caminhoMdb)}
    # Executável fixo, sem shell; o caminho do banco vai por variável de ambiente, não pelo script.
    res = subprocess.run(  # noqa: S603  # nosec B603
        [_caminhoPowerShell(), "-NoProfile", "-NonInteractive", "-Command", psScript],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=ambiente,
    )
    bruto: dict[str, Any] = json.loads(res.stdout.strip())
    return bruto


def _distanciaOuNulo(valor: int | None) -> int | None:
    """No Helga, distância zero é campo não informado: fica ausente (nulo), nunca estimada."""
    return valor if valor is not None and valor > 0 else None


def _segundosDoTempo(tempo: str | None) -> int | None:
    """Converte `hh:mm:ss` em segundos; texto ausente ou fora do formato devolve None."""
    if not tempo:
        return None
    partes = tempo.split(":")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        return None
    return int(partes[0]) * 3600 + int(partes[1]) * 60 + int(partes[2])


def montarParciais(bruto: dict[str, Any], fonte: str, sha256Fonte: str) -> dict[str, Any]:
    """Monta o JSON de parciais a partir da leitura bruta (spec analise-desempenho, Camada B).

    Para cada concluinte vale a última leitura do chip (maior id). As parciais só são aceitas quando a soma,
    incluindo o posto de chegada (999), iguala o tempo oficial (tolerância de 1 s); caso contrário o concluinte
    vai para `ocorrencias`. Sequência de postos diferente da do percurso mantém as parciais, com
    `postosConferem` falso e uma ocorrência. Nada é corrigido. Categorias não competitivas (acompanhadas e
    abertas) ficam de fora, assim como os percursos que só elas usavam.
    """
    postosPorPercurso: dict[int, list[dict[str, Any]]] = {}
    for p in sorted(bruto["postos"], key=lambda p: (p["percursoId"], p["ordem"])):
        postosPorPercurso.setdefault(p["percursoId"], []).append({
            "ordem": p["ordem"], "codigoPosto": p["codigoPosto"], "distanciaM": _distanciaOuNulo(p["distanciaM"]),
        })

    ultimaLeitura: dict[tuple[int, int], int] = {}
    for leitura in bruto["leituras"]:
        if leitura["chip"] is None:
            continue
        chave = (leitura["competitionId"], leitura["chip"])
        ultimaLeitura[chave] = max(ultimaLeitura.get(chave, 0), leitura["leituraId"])

    passagensPorLeitura: dict[int, list[dict[str, Any]]] = {}
    for passagem in sorted(bruto["passagens"], key=lambda p: (p["leituraId"], p["ordem"])):
        passagensPorLeitura.setdefault(passagem["leituraId"], []).append(passagem)

    participacoes: list[dict[str, Any]] = []
    ocorrencias: list[dict[str, Any]] = []

    def recusar(c: dict[str, Any], motivo: str) -> None:
        ocorrencias.append({"competitionId": c["competitionId"], "runnerPk": c["runnerPk"], "motivo": motivo})

    concluintes = sorted(
        (c for c in bruto["concluintes"] if not ehCategoriaNaoCompetitiva(c["categoria"])),
        key=lambda c: (c["competitionId"], c["runnerPk"]),
    )
    percursosUsados = {c["percursoId"] for c in concluintes}
    for c in concluintes:
        oficial = _segundosDoTempo(c["tempo"])
        if c["percursoId"] is None:
            recusar(c, "sem percurso")
        elif oficial is None:
            recusar(c, "sem tempo oficial")
        elif c["chip"] is None:
            recusar(c, "sem chip registrado")
        elif (c["competitionId"], c["chip"]) not in ultimaLeitura:
            recusar(c, "sem leitura do chip")
        else:
            lidas = passagensPorLeitura.get(ultimaLeitura[(c["competitionId"], c["chip"])], [])
            if not lidas:
                recusar(c, "última leitura sem passagens")
            elif any(p["tempoParcialSegundos"] is None for p in lidas):
                recusar(c, "parcial ausente na última leitura")
            else:
                soma = sum(p["tempoParcialSegundos"] for p in lidas)
                if abs(soma - oficial) > TOLERANCIA_SOMA_SEGUNDOS:
                    recusar(c, f"soma das parciais ({soma} s) diverge do tempo oficial ({oficial} s)")
                    continue
                esperada = [p["codigoPosto"] for p in postosPorPercurso.get(c["percursoId"], [])]
                conferem = esperada == [p["codigoPosto"] for p in lidas]
                if not conferem:
                    recusar(c, "sequência de postos lida difere da do percurso")
                participacoes.append({
                    "competitionId": c["competitionId"], "runnerPk": c["runnerPk"], "percursoId": c["percursoId"],
                    "tempoOficialSegundos": oficial,
                    "passagens": [
                        {"ordem": i, "codigoPosto": p["codigoPosto"], "tempoParcialSegundos": p["tempoParcialSegundos"]}
                        for i, p in enumerate(lidas, start=1)
                    ],
                    "postosConferem": conferem,
                })

    dados: dict[str, Any] = {
        "fonte": fonte,
        "sha256Fonte": sha256Fonte,
        "percursos": [
            {"percursoId": pid, "postos": postos} for pid, postos in sorted(postosPorPercurso.items())
            if pid in percursosUsados
        ],
        "participacoes": participacoes,
        "ocorrencias": ocorrencias,
    }
    validarDadosParciais(dados)
    return dados


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai as parciais por posto do HelgaDat.mdb para JSON.")
    parser.add_argument("--ano", type=int, default=2026, help="Ano da edição (preenche os caminhos padrão)")
    parser.add_argument("--mdb", default=None, help="Caminho do arquivo .mdb do Helga")
    parser.add_argument("--saida", default=None, help="Caminho do JSON de saída")
    args = parser.parse_args()

    caminhoMdb = args.mdb or f"Dados/{args.ano}/entradas/HelgaDat.mdb"
    caminhoSaida = args.saida or f"Dados/{args.ano}/extraidos/parciaisHelga{args.ano}.json"

    if not os.path.isfile(caminhoMdb):
        print(f"Arquivo não encontrado: {caminhoMdb}", file=sys.stderr)
        return 1

    fonte = os.path.basename(caminhoMdb)
    sha256 = calcularSha256(caminhoMdb)
    try:
        conferirHashNoManifesto(
            {"fonte": fonte, "sha256Fonte": sha256}, args.ano, os.path.join(RAIZ, "Dados"),
        )
        dados = montarParciais(extrairBrutoViaPowerShellOdbc(caminhoMdb), fonte, sha256)
    except EntradaInvalidaError as erro:
        print(f"Extração recusada: {erro}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaida)), exist_ok=True)
    with open(caminhoSaida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(
        f"Extração concluída: {len(dados['percursos'])} percursos, "
        f"{len(dados['participacoes'])} participações com parciais, "
        f"{len(dados['ocorrencias'])} ocorrências -> {caminhoSaida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
