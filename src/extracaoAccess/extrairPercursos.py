#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extrai os percursos de um arquivo Helga (.mdb/.accdb) para JSON em Dados/<ano>/extraidos/.

Camada A da spec analise-desempenho: distância e subida de cada percurso, percurso de cada categoria e
percurso de cada participação. Não altera o JSON da apuração; o vínculo é por `competitionId` e `runnerPk`.
Só roda sobre arquivo cujo SHA-256 esteja no manifesto de arquivos congelados.
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

from src.extracaoAccess.extrairHelga import _caminhoPowerShell  # noqa: E402
from src.extracaoAccess.inspecionarBanco import calcularSha256  # noqa: E402
from src.extracaoAccess.validarEntrada import (  # noqa: E402
    EntradaInvalidaError,
    conferirHashNoManifesto,
    validarDadosPercursos,
)

STATUS_CONCLUIU = 0


def extrairBrutoViaPowerShellOdbc(caminhoMdb: str) -> dict[str, Any]:
    """Lê Parcours, Cat_Parc e Course via .NET OdbcConnection, em modo somente leitura."""
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

function TextoOuNulo($v) {
    if ($v -is [System.DBNull] -or "$v" -eq "") { return $null }
    return "$v"
}

$etapas = "(SELECT ID FROM Competition WHERE Event_FK >= 2)"

$percursos = @()
foreach ($r in (Get-Rows "SELECT ID, Competition_FK, Number, ParcName, Length, Climbing FROM Parcours WHERE Competition_FK IN $etapas ORDER BY ID")) {
    $percursos += [ordered]@{
        percursoId = [int]$r.ID
        competitionId = [int]$r.Competition_FK
        numero = [int]$r.Number
        nome = "$($r.ParcName)".Trim()
        distanciaM = IntOuNulo $r.Length
        subidaM = IntOuNulo $r.Climbing
    }
}

$categoriaPercurso = @()
foreach ($r in (Get-Rows "SELECT cp.Competition_PK, cp.Category_PK, cat.Name AS CatName, cp.Parcours_PK FROM Cat_Parc cp INNER JOIN Categories cat ON cp.Category_PK = cat.ID WHERE cp.Competition_PK IN $etapas ORDER BY cp.Competition_PK, cat.Name")) {
    $categoriaPercurso += [ordered]@{
        competitionId = [int]$r.Competition_PK
        categoriaId = [int]$r.Category_PK
        categoria = "$($r.CatName)".Trim()
        percursoId = [int]$r.Parcours_PK
    }
}

$participacoes = @()
foreach ($r in (Get-Rows "SELECT Competition_PK, Runner_PK, Parcours_FK, Status_FK, Format(StartTime, 'hh:nn:ss') AS Largada, Format(FinishTime, 'hh:nn:ss') AS Chegada FROM Course WHERE Competition_PK IN $etapas ORDER BY Competition_PK, Runner_PK")) {
    $participacoes += [ordered]@{
        competitionId = [int]$r.Competition_PK
        runnerPk = [int]$r.Runner_PK
        percursoId = IntOuNulo $r.Parcours_FK
        statusCodigo = [int]$r.Status_FK
        horaLargada = TextoOuNulo $r.Largada
        horaChegada = TextoOuNulo $r.Chegada
    }
}

$conn.Close()

$out = [ordered]@{
    percursos = $percursos
    categoriaPercurso = $categoriaPercurso
    participacoes = $participacoes
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


def _valorOuNulo(valor: Any) -> int | None:
    """No Helga, zero em distância ou subida é campo não informado: fica ausente (nulo), nunca estimado."""
    if valor is None or valor <= 0:
        return None
    return int(valor)


def montarPercursos(bruto: dict[str, Any], fonte: str, sha256Fonte: str) -> dict[str, Any]:
    """Monta o JSON de percursos a partir da leitura bruta e recusa o que a Camada A não aceita.

    Recusa (listando todos os problemas): participação que concluiu (`statusCodigo` 0) sem percurso, com
    percurso inexistente ou sem distância. Quem não concluiu pode ficar sem percurso.
    """
    percursos = [
        {
            "percursoId": p["percursoId"], "competitionId": p["competitionId"], "numero": p["numero"],
            "nome": p["nome"], "distanciaM": _valorOuNulo(p["distanciaM"]), "subidaM": _valorOuNulo(p["subidaM"]),
        }
        for p in sorted(bruto["percursos"], key=lambda p: p["percursoId"])
    ]
    porId = {p["percursoId"]: p for p in percursos}

    erros: list[str] = []
    for part in bruto["participacoes"]:
        if part["statusCodigo"] != STATUS_CONCLUIU:
            continue
        origem = f"competitionId {part['competitionId']}, runnerPk {part['runnerPk']}"
        percursoId = part["percursoId"]
        if percursoId is None:
            erros.append(f"{origem}: concluiu sem percurso")
        elif percursoId not in porId:
            erros.append(f"{origem}: percurso {percursoId} inexistente")
        elif porId[percursoId]["distanciaM"] is None:
            erros.append(f"{origem}: percurso {percursoId} sem distância (Length ausente ou zero)")
    if erros:
        resumo = erros[:20]
        if len(erros) > 20:
            resumo.append(f"... e mais {len(erros) - 20} problema(s)")
        raise EntradaInvalidaError("; ".join(resumo))

    participacoes = [
        {
            "competitionId": p["competitionId"], "runnerPk": p["runnerPk"], "percursoId": p["percursoId"],
            "horaLargada": p["horaLargada"], "horaChegada": p["horaChegada"],
        }
        for p in sorted(bruto["participacoes"], key=lambda p: (p["competitionId"], p["runnerPk"]))
    ]
    categoriaPercurso = sorted(
        bruto["categoriaPercurso"], key=lambda c: (c["competitionId"], c["categoria"], c["categoriaId"]),
    )
    dados: dict[str, Any] = {
        "fonte": fonte,
        "sha256Fonte": sha256Fonte,
        "percursos": percursos,
        "categoriaPercurso": categoriaPercurso,
        "participacoes": participacoes,
    }
    validarDadosPercursos(dados)
    return dados


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai os percursos do HelgaDat.mdb para JSON.")
    parser.add_argument("--ano", type=int, default=2026, help="Ano da edição (preenche os caminhos padrão)")
    parser.add_argument("--mdb", default=None, help="Caminho do arquivo .mdb do Helga")
    parser.add_argument("--saida", default=None, help="Caminho do JSON de saída")
    args = parser.parse_args()

    caminhoMdb = args.mdb or f"Dados/{args.ano}/entradas/HelgaDat.mdb"
    caminhoSaida = args.saida or f"Dados/{args.ano}/extraidos/percursosHelga{args.ano}.json"

    if not os.path.isfile(caminhoMdb):
        print(f"Arquivo não encontrado: {caminhoMdb}", file=sys.stderr)
        return 1

    fonte = os.path.basename(caminhoMdb)
    sha256 = calcularSha256(caminhoMdb)
    try:
        conferirHashNoManifesto(
            {"fonte": fonte, "sha256Fonte": sha256}, args.ano, os.path.join(RAIZ, "Dados"),
        )
        dados = montarPercursos(extrairBrutoViaPowerShellOdbc(caminhoMdb), fonte, sha256)
    except EntradaInvalidaError as erro:
        print(f"Extração recusada: {erro}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(caminhoSaida)), exist_ok=True)
    with open(caminhoSaida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(
        f"Extração concluída: {len(dados['percursos'])} percursos, "
        f"{len(dados['categoriaPercurso'])} vínculos categoria-percurso, "
        f"{len(dados['participacoes'])} participações -> {caminhoSaida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
