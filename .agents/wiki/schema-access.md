---
description: Mapeamento das tabelas, colunas e códigos de status do banco de dados Microsoft Access (HelgaDat.mdb) do software Helga.
---

# Esquema do Banco de Dados Microsoft Access (`HelgaDat.mdb`)

Última atualização: 2026-11-14

Esta página documenta a estrutura real das tabelas do software de apuração **Helga** (`HelgaDat.mdb`), inspecionada a partir do banco oficial da temporada 2026.

## Como extrair os dados higienizados de um banco Helga

Coloque o arquivo `HelgaDat.mdb` em `Dados/<ano>/entradas/` (protegido pelo `.gitignore`) junto com `voluntariosCCO.md` e execute:

```powershell
python src/extracaoAccess/extrairHelga.py --mdb "Dados/2026/entradas/HelgaDat.mdb" --saida "Dados/2026/extraidos/etapasHelga2026.json"
```

Para a análise de desempenho (distância e subida dos percursos), extraia também os percursos:

```powershell
python src/extracaoAccess/extrairPercursos.py --ano 2026
```

O arquivo `Dados/<ano>/extraidos/percursosHelga<ano>.json` só é gerado se o hash do `.mdb` constar do manifesto, e seu ritmo se consulta com `python src/analises/ritmoAtletas.py --ano <ano>`.

## Tabelas Principais do `HelgaDat.mdb`

| Tabela no Access | Papel na Apuração | Campos Utilizados (Higienizados) | Campos Ignorados (LGPD / Internos) |
| :--- | :--- | :--- | :--- |
| `Event` | Eventos cadastrados (`Event_FK >= 2` corresponde às etapas do campeonato estadual) | `ID`, `Description`, `Location`, `Organisor_FK`, `DateFrom` | `GUID`, `LockedMachineName` |
| `Competition` | Percursos/etapas de cada evento (em 2026: IDs `35`, `36`, `37` e `38`) | `ID`, `Site`, `OrganisingClub_FK`, `Event_FK`, `CompDate`, `Description` | Custos de inscrição (`NormalCost`, etc.), `Token` |
| `Club` | Clubes e federações vinculadas | `ID`, `Code`, `Name`, `Short_Name`, `Federation_FK` (`208` = FECORI; IDs `30` e `361` = Individual sem clube) | `Logo`, `Contact_FK`, `Homepage` |
| `Federation` | Federações estaduais e CBO | `ID`, `Name`, `LongName` | `DB_updated` |
| `Categories` | Categorias disputadas | `ID`, `Name`, `Age`, `Gender` (`DN1..3` e `HN1..3` são categorias acompanhadas) | `Order`, `Order2` |
| `Person` | Cadastro de atletas | `ID`, `Code` (número CBO), `Firstname`, `Name`, `Gender`, `Club_FK`, `Category_FK` | `Street1`, `Street2`, `Zip`, `Town`, `Phone1`, `Phone2`, `Fax`, `Email`, `Birthdate` e `YearOfBirth` (nenhuma data ou ano de nascimento é extraído; ver [ADR-003](decisions/ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)) |
| `Course` | Inscrições, tempos e status por etapa | `Competition_PK`, `Runner_PK`, `Category_FK`, `Club_FK`, `Status_FK`, `ClassifyYN`, `CourseTime`, `CourseTime_ms`; para a análise de desempenho também `Parcours_FK`, `StartTime` e `FinishTime` | `EmitBadge`, `Rented`, `RealBadgeNumber` |
| `Parcours` | Percursos de cada etapa (análise de desempenho, [spec](../specs/analise-desempenho/spec.md)) | `ID`, `Competition_FK`, `Number`, `ParcName`, `Length` (distância em metros) e `Climbing` (subida em metros); zero significa não informado | `VariationName`, `NbMaps`, `PenaltyGap`, `Box_FK` |
| `Cat_Parc` | Percurso de cada categoria em cada etapa (análise de desempenho) | `Competition_PK`, `Category_PK`, `Parcours_PK` | `StartFrom`, `StartStep`, `TimeLimit` (vazio em 2026) |
| `Status` | Dicionário de status de chegada | `code`, `status`, `status_short` | — |

## Códigos da Tabela `Status` e Regra de Pontuação (Art. 31)

> **Atenção:** O campo booleano `Course.NotStarted` no Helga nem sempre é atualizado quando o atleta parte e conclui o percurso (ex.: atletas com `Status_FK = 0` e tempo válido, mas `NotStarted = True`). Por isso, a situação do atleta é determinada exclusivamente pelo campo **`Course.Status_FK`**.

| `Status_FK` | `status_short` | Descrição no Helga | Tratamento no Regulamento 2026 (Art. 31) |
| :---: | :---: | :--- | :--- |
| `0` | `OK` | Concluiu o percurso com sucesso | Classificado por ordem crescente de `CourseTime`: 1º ao 26º recebe `40..11` pontos; 27º em diante recebe `10` pontos |
| `1` | `NC` | Não classificado (erro de ponto / falta de prisma) | Recebe **1 ponto** pela participação (Art. 31, § 2º) |
| `2` | `DC` | Desclassificado | Recebe **1 ponto** pela participação (Art. 31, § 2º) |
| `3` | `NP` | Não partiu | Recebe **0 pontos** (não participou da etapa) |
| `4` | `NT` | Sem tempo (*no time*) | Recebe **1 ponto** pela participação |
| `5` | `OT` | Acima do tempo limite (*over time*) | Recebe **1 ponto** pela participação (Art. 31, § 2º) |
| `6` | `DNF` | Desistiu (*did not finish*) | Recebe **1 ponto** pela participação (Art. 31, § 2º) |
| `98` | `CC` | Inscrição cancelada (*Cancelled*) | Recebe **0 pontos** (participação cancelada no evento) |
