#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extrai os dados higienizados (LGPD) de um arquivo Helga (.mdb/.accdb)
para JSON estruturado em Dados/<ano>/extraidos/ e registra seu SHA-256.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from typing import Any

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.extracaoAccess.leitorVoluntarios import lerVoluntariosMarkdown


def calcularSha256(caminhoArquivo: str) -> str:
    """Calcula o hash SHA-256 de um arquivo em disco."""
    hasher = hashlib.sha256()
    with open(caminhoArquivo, 'rb') as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b''):
            hasher.update(bloco)
    return hasher.hexdigest()


def extrairDadosViaPowerShellOdbc(caminhoMdb: str) -> dict[str, Any]:
    """Lê as tabelas Competition, Club, Categories, Person e Course via .NET OdbcConnection
    no Windows PowerShell (64-bit), retornando apenas os campos esportivos higienizados.
    """
    caminhoAbs = os.path.abspath(caminhoMdb).replace("'", "''")
    psScript = f"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$conn = New-Object System.Data.Odbc.OdbcConnection("Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};Dbq={caminhoAbs};ReadOnly=1;")
$conn.Open()

function Get-Rows($sql) {{
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $da = New-Object System.Data.Odbc.OdbcDataAdapter($cmd)
    $dt = New-Object System.Data.DataTable
    [void]$da.Fill($dt)
    return $dt.Rows
}}

$etapasRows = Get-Rows "SELECT c.ID, c.Site, c.OrganisingClub_FK, cl.Short_Name AS OrgShort, c.Event_FK, c.CompDate, c.Description FROM Competition c LEFT JOIN Club cl ON c.OrganisingClub_FK = cl.ID WHERE c.Event_FK >= 2 ORDER BY c.ID"
$etapas = @()
$idx = 1
foreach ($r in $etapasRows) {{
    $etapas += [ordered]@{{
        numeroEtapa = $idx
        competitionId = [int]$r.ID
        eventId = [int]$r.Event_FK
        descricao = "$($r.Description)".Trim()
        local = "$($r.Site)".Trim()
        data = ([datetime]$r.CompDate).ToString('yyyy-MM-dd')
        clubeOrganizadorId = [int]$r.OrganisingClub_FK
        clubeOrganizadorSigla = "$($r.OrgShort)".Trim()
    }}
    $idx++
}}

$clubesRows = Get-Rows "SELECT cl.ID, cl.Code, cl.Name, cl.Short_Name, cl.Federation_FK, f.Name AS FedSigla FROM Club cl LEFT JOIN Federation f ON cl.Federation_FK = f.ID ORDER BY cl.ID"
$clubes = @()
foreach ($r in $clubesRows) {{
    $fedId = if ($r.Federation_FK -isnot [System.DBNull] -and "$($r.Federation_FK)" -ne "") {{ [int]$r.Federation_FK }} else {{ $null }}
    $clubes += [ordered]@{{
        clubeId = [int]$r.ID
        codigoCBO = [int]$r.Code
        sigla = "$($r.Short_Name)".Trim()
        nome = "$($r.Name)".Trim()
        federacaoId = $fedId
        federacaoSigla = if ($r.FedSigla -isnot [System.DBNull]) {{ "$($r.FedSigla)".Trim() }} else {{ $null }}
        filiadoCBO = [bool]($fedId -ne $null -and $fedId -gt 0 -and [int]$r.ID -notin @(30, 361))
    }}
}}

$sqlCourse = @"
SELECT
    c.Competition_PK,
    c.Runner_PK,
    p.Code AS CBO,
    p.Firstname,
    p.Name AS Lastname,
    p.Gender,
    p.YearOfBirth,
    Format(p.Birthdate, 'yyyy') AS BirthYearFromDate,
    c.Club_FK,
    cl.Short_Name AS ClubShort,
    cl.Name AS ClubName,
    cl.Federation_FK,
    c.Category_FK,
    cat.Name AS CatName,
    c.Status_FK,
    s.status_short AS StatusShort,
    c.ClassifyYN,
    Format(c.CourseTime, 'hh:nn:ss') AS TempoStr,
    c.CourseTime_ms
FROM ((((Course c
    INNER JOIN Person p ON c.Runner_PK = p.ID)
    INNER JOIN Categories cat ON c.Category_FK = cat.ID)
    LEFT JOIN Club cl ON c.Club_FK = cl.ID)
    LEFT JOIN Status s ON c.Status_FK = s.code)
WHERE c.Competition_PK IN (SELECT ID FROM Competition WHERE Event_FK >= 2)
ORDER BY c.Competition_PK, cat.Name, c.Status_FK, c.CourseTime
"@

$courseRows = Get-Rows $sqlCourse
$registros = @()
foreach ($r in $courseRows) {{
    $nomeCompleto = ("$($r.Firstname) $($r.Lastname)").Trim()
    $anoNasc = if ($r.YearOfBirth -isnot [System.DBNull] -and [int]$r.YearOfBirth -gt 0) {{
        [int]$r.YearOfBirth
    }} elseif ($r.BirthYearFromDate -isnot [System.DBNull] -and "$($r.BirthYearFromDate)" -match '^\\d{{4}}$') {{
        [int]$r.BirthYearFromDate
    }} else {{
        $null
    }}
    $tempoStr = if ($r.TempoStr -isnot [System.DBNull] -and "$($r.TempoStr)" -ne "") {{ "$($r.TempoStr)" }} else {{ $null }}
    $tempoSeg = $null
    if ($tempoStr -match '^(\\d{{2}}):(\\d{{2}}):(\\d{{2}})$') {{
        $tempoSeg = ([int]$Matches[1] * 3600) + ([int]$Matches[2] * 60) + [int]$Matches[3]
    }}
    $fedId = if ($r.Federation_FK -isnot [System.DBNull] -and "$($r.Federation_FK)" -ne "") {{ [int]$r.Federation_FK }} else {{ $null }}
    $clubeId = if ($r.Club_FK -isnot [System.DBNull]) {{ [int]$r.Club_FK }} else {{ 0 }}

    $registros += [ordered]@{{
        competitionId = [int]$r.Competition_PK
        runnerPk = [int]$r.Runner_PK
        cbo = [int]$r.CBO
        nome = $nomeCompleto
        sexo = if ($r.Gender -isnot [System.DBNull]) {{ [int]$r.Gender }} else {{ $null }}
        anoNascimento = $anoNasc
        clubeId = $clubeId
        clubeSigla = "$($r.ClubShort)".Trim()
        clubeNome = "$($r.ClubName)".Trim()
        clubeFiliadoCBO = [bool]($fedId -ne $null -and $fedId -gt 0 -and $clubeId -notin @(0, 30, 361))
        categoriaId = [int]$r.Category_FK
        categoria = "$($r.CatName)".Trim()
        statusCodigo = [int]$r.Status_FK
        statusSigla = "$($r.StatusShort)".Trim()
        classifyYN = [bool]$r.ClassifyYN
        tempo = $tempoStr
        tempoSegundos = $tempoSeg
        tempoMs = if ($r.CourseTime_ms -isnot [System.DBNull] -and "$($r.CourseTime_ms)" -ne "") {{ [int]$r.CourseTime_ms }} else {{ 0 }}
    }}
}}

$pRows = Get-Rows "SELECT p.ID, p.Code AS CBO, p.Firstname, p.Name AS Lastname, p.Gender, p.YearOfBirth, Format(p.Birthdate, 'yyyy') AS BirthYearFromDate, p.Club_FK, cl.Short_Name AS ClubShort, cl.Name AS ClubName, cl.Federation_FK, p.Category_FK, cat.Name AS CatName FROM (Person p LEFT JOIN Club cl ON p.Club_FK = cl.ID) LEFT JOIN Categories cat ON p.Category_FK = cat.ID WHERE p.Code > 0"
$cadastroAtletas = @{{}}
foreach ($r in $pRows) {{
    $cboKey = "$([int]$r.CBO)"
    $anoNasc = if ($r.YearOfBirth -isnot [System.DBNull] -and [int]$r.YearOfBirth -gt 0) {{
        [int]$r.YearOfBirth
    }} elseif ($r.BirthYearFromDate -isnot [System.DBNull] -and "$($r.BirthYearFromDate)" -match '^\\d{{4}}$') {{
        [int]$r.BirthYearFromDate
    }} else {{
        $null
    }}
    $fedId = if ($r.Federation_FK -isnot [System.DBNull] -and "$($r.Federation_FK)" -ne "") {{ [int]$r.Federation_FK }} else {{ $null }}
    $clubeId = if ($r.Club_FK -isnot [System.DBNull]) {{ [int]$r.Club_FK }} else {{ 0 }}
    $cadastroAtletas[$cboKey] = [ordered]@{{
        cbo = [int]$r.CBO
        nome = ("$($r.Firstname) $($r.Lastname)").Trim()
        sexo = if ($r.Gender -isnot [System.DBNull]) {{ [int]$r.Gender }} else {{ $null }}
        anoNascimento = $anoNasc
        clubeId = $clubeId
        clubeSigla = "$($r.ClubShort)".Trim()
        clubeNome = "$($r.ClubName)".Trim()
        clubeFiliadoCBO = [bool]($fedId -ne $null -and $fedId -gt 0 -and $clubeId -notin @(0, 30, 361))
        categoriaPadrao = if ($r.CatName -isnot [System.DBNull]) {{ "$($r.CatName)".Trim() }} else {{ $null }}
    }}
}}

$conn.Close()

$out = [ordered]@{{
    etapas = $etapas
    clubes = $clubes
    registros = $registros
    cadastroPorCBO = $cadastroAtletas
}}
$out | ConvertTo-Json -Depth 6 -Compress
"""
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", psScript],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(res.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrai dados higienizados do HelgaDat.mdb para JSON."
    )
    parser.add_argument(
        "--mdb",
        default="Dados/2026/entradas/HelgaDat.mdb",
        help="Caminho do arquivo .mdb do Helga",
    )
    parser.add_argument(
        "--saida",
        default="Dados/2026/extraidos/etapasHelga2026.json",
        help="Caminho do arquivo JSON higienizado de saída",
    )
    parser.add_argument(
        "--voluntarios",
        default="Dados/2026/entradas/voluntariosCCO.md",
        help="Arquivo Markdown de voluntários para garantir inclusão do perfil base se necessário",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.mdb):
        print(f"Arquivo não encontrado: {args.mdb}", file=sys.stderr)
        return 1

    sha256 = calcularSha256(args.mdb)
    dadosBrutos = extrairDadosViaPowerShellOdbc(args.mdb)

    cbosNasEtapas = {str(r["cbo"]) for r in dadosBrutos["registros"]}
    if os.path.isfile(args.voluntarios):
        with open(args.voluntarios, encoding="utf-8") as fh:
            volData = lerVoluntariosMarkdown(fh.read())
        for v in volData.get("voluntarios", []):
            cbosNasEtapas.add(str(v["cbo"]))
        for u in volData.get("unificacoesCbo", []):
            cbosNasEtapas.add(str(u["cboOficial"]))

    perfisFiltrados = {
        cbo: perfil
        for cbo, perfil in dadosBrutos["cadastroPorCBO"].items()
        if cbo in cbosNasEtapas
    }

    clubesUsadosIds = {r["clubeId"] for r in dadosBrutos["registros"]} | {
        p["clubeId"] for p in perfisFiltrados.values()
    }
    clubesFiltrados = [
        c for c in dadosBrutos["clubes"] if c["clubeId"] in clubesUsadosIds
    ]

    compIdParaEtapa = {
        e["competitionId"]: e["numeroEtapa"] for e in dadosBrutos["etapas"]
    }
    for r in dadosBrutos["registros"]:
        r["etapa"] = compIdParaEtapa[r["competitionId"]]

    payloadFinal = {
        "fonte": os.path.basename(args.mdb),
        "sha256Fonte": sha256,
        "etapas": dadosBrutos["etapas"],
        "clubes": clubesFiltrados,
        "perfisAtletas": perfisFiltrados,
        "registrosEtapas": dadosBrutos["registros"],
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    with open(args.saida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payloadFinal, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(
        f"Extração concluída: {len(dadosBrutos['etapas'])} etapas, "
        f"{len(dadosBrutos['registros'])} inscrições, "
        f"{len(perfisFiltrados)} atletas únicos -> {args.saida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
