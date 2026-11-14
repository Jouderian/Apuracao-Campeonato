---
description: Dicionário de dados da base SQLite de análise de desempenho — tabelas, colunas, unidades, regras de leitura e consultas de exemplo, para quem (ou qual IA) vai consultá-la.
---

# Dicionário de Dados da Base de Análise de Desempenho

Última atualização: 2026-11-14

Leia esta página antes de consultar a base ([ADR-009](decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md), [spec](../specs/analise-desempenho/spec.md)). A base é derivada dos JSON higienizados e não é versionada.

## Como gerar e consultar

```powershell
python src/analises/gerarBase.py                       # cria Dados/analise/analiseCCO.sqlite a partir dos JSON
python src/analises/consultar.py "SELECT ..."          # um único SELECT, somente leitura, até 200 linhas
python src/analises/consultar.py "SELECT ..." --limite 1000 --json
```

`consultar.py` abre a base em modo somente leitura, aceita só `SELECT` (ou `WITH ... SELECT`) e interrompe consultas longas demais. A conta (média, contagem, ordenação) é feita pelo SQL; quem responde cita a consulta usada.

## Regras de leitura

1. **Informativo:** nada aqui entra na apuração. Pontuação, descarte, desempate e clubes vêm só do motor de cálculo.
2. **Ritmo** é em segundos por quilômetro (`ritmoSegundosPorKm`), arredondado ao segundo com a metade para cima; `ritmoTexto` mostra `m'ss"`. Só existe para quem concluiu (`statusCodigo` 0), com tempo e percurso com distância. Em empate exato de meio segundo o site do HelgaO pode diferir 1 s.
3. **Comparação:** ritmos só se comparam dentro da mesma categoria ou do mesmo percurso. Não há ritmo ajustado pela subida.
4. **Nulo é dado ausente, nunca zero:** `NULL` em distância, subida ou ritmo significa que o Helga não informou ou que não se pôde calcular. Não estime; explique a ausência (`motivoSemRitmo`).
5. **`competitionId` repete-se entre anos:** una sempre por `ano` junto.
6. **Cobertura:** 2024 e 2026 têm as quatro etapas, com percursos e parciais. Em 2025 entram só as etapas 1 e 4; as etapas 2 e 3 foram apuradas pela planilha do site e ficam fora. Na etapa 4 de 2024, muitas parciais ficaram em `ocorrenciaParcial` porque a soma não fecha o tempo oficial.
7. **Distância do trecho** vem de `Controls.Distance` do Helga; a soma dos trechos fica de 0,3% a 1,7% abaixo da distância do percurso (8 percursos de 2026 medidos). O ritmo por trecho não reproduz exatamente o ritmo do percurso.
8. **Parciais** valem a última leitura do chip e só são aceitas quando a soma fecha o tempo oficial (tolerância de 1 s); as demais estão em `ocorrenciaParcial`. Segundo o apurador, parte da diferença pode vir de relógios das bases das parciais fora de sincronia (hipótese não verificada nos dados).
9. **Categorias não competitivas ficam de fora:** as acompanhadas (`HN1` a `HN3`, `DN1` a `DN3`), sem classificação, e o percurso aberto (`Aberto ...`), que não pontua, não entram na base, conforme os regulamentos de 2024 a 2026 (decisão do apurador, 2026-11-14).
10. **Privacidade:** a base não tem ano de nascimento nem dado pessoal além do nome e do CBO já presentes nos JSON; não há recorte por idade, só por categoria.

## Tabelas e visões

### `metadado`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `chave` | TEXT | `aviso` (natureza informativa), `anos` (anos carregados) e `dicionario` (esta página). |
| `valor` | TEXT | Valor da chave. |

### `fonte`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `arquivo` | TEXT | JSON higienizado lido (`etapasHelga<ano>.json`, `percursosHelga<ano>.json`, `parciaisHelga<ano>.json`). |
| `sha256` | TEXT | SHA-256 do arquivo original do Helga, o mesmo de `Dados/arquivosCongelados.sha256`. |

### `etapa`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `numeroEtapa` | INTEGER | Número da etapa no campeonato (1 a 4). |
| `competitionId` | INTEGER | Identificador da etapa no Helga; repete-se entre anos. |
| `data` | TEXT | Data da etapa, `AAAA-MM-DD`. |
| `local` | TEXT | Local da etapa. |
| `clubeOrganizadorSigla` | TEXT | Sigla do clube organizador. |

### `percurso`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `competitionId` | INTEGER | Etapa do percurso. |
| `percursoId` | INTEGER | Identificador do percurso no Helga. |
| `numero` | INTEGER | Número do percurso na etapa. |
| `distanciaM` | INTEGER | Distância do percurso em metros (`Parcours.Length`); nulo quando não informada. |
| `subidaM` | INTEGER | Subida do percurso em metros (`Parcours.Climbing`); nulo quando não informada (zero no Helga). |

### `participacao`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `numeroEtapa` | INTEGER | Número da etapa. |
| `competitionId` | INTEGER | Etapa no Helga. |
| `runnerPk` | INTEGER | Identificador do atleta no Helga (chave junto com `ano` e `competitionId`). |
| `cbo` | INTEGER | Número CBO do atleta, a chave para acompanhar o atleta entre etapas e anos. |
| `nome` | TEXT | Nome do atleta. |
| `clubeSigla` | TEXT | Sigla do clube na etapa. |
| `categoria` | TEXT | Categoria disputada, por exemplo `H Adulto E`. |
| `statusCodigo` | INTEGER | Situação de chegada: 0 concluiu (`OK`), 1 não classificado, 2 desclassificado, 3 não partiu, 4 sem tempo, 5 acima do tempo limite, 6 desistiu, 98 inscrição cancelada. |
| `statusSigla` | TEXT | Sigla da situação (`OK`, `NC`, `DC`, `NP`, `NT`, `OT`, `DNF`, `CC`). |
| `tempoSegundos` | INTEGER | Tempo oficial em segundos; nulo quando não há tempo. |
| `percursoId` | INTEGER | Percurso do atleta (não o da categoria); nulo quando o ano não tem percursos. |
| `distanciaM` | INTEGER | Distância do percurso do atleta, em metros. |
| `ritmoSegundosPorKm` | INTEGER | Ritmo médio em segundos por quilômetro; nulo quando não pôde ser calculado. |
| `ritmoTexto` | TEXT | O mesmo ritmo como `m'ss"`. |
| `motivoSemRitmo` | TEXT | Quando não há ritmo: `não concluiu (<sigla>)`, `sem tempo`, `sem percurso` ou `percurso sem distância`. |

### `parcial`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `competitionId` | INTEGER | Etapa no Helga. |
| `runnerPk` | INTEGER | Atleta no Helga; liga-se a `participacao`. |
| `ordem` | INTEGER | Ordem do trecho na leitura, a partir de 1 (o primeiro parte da largada). |
| `codigoPosto` | INTEGER | Código do posto em que o trecho termina; 999 é a chegada. |
| `distanciaM` | INTEGER | Distância do trecho em metros; nula quando a sequência de postos não confere ou o trecho não tem distância. |
| `tempoParcialSegundos` | INTEGER | Tempo do trecho em segundos. |
| `ritmoSegundosPorKm` | INTEGER | Ritmo do trecho em segundos por quilômetro; nulo quando não há distância do trecho. |
| `ritmoTexto` | TEXT | O mesmo ritmo como `m'ss"`. |
| `postosConferem` | INTEGER | 1 quando a sequência de postos lida é igual à do percurso; 0 quando difere (posto pulado ou repetido). |

### `ocorrenciaParcial`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `competitionId` | INTEGER | Etapa no Helga. |
| `runnerPk` | INTEGER | Atleta no Helga. |
| `motivo` | TEXT | Por que as parciais não foram aceitas ou conferem só em parte, por exemplo a soma das parciais divergir do tempo oficial. |

### `vwRitmo`

Participações que têm ritmo, com data e local da etapa. Use-a para comparar ritmos.

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `numeroEtapa` | INTEGER | Número da etapa. |
| `data` | TEXT | Data da etapa. |
| `local` | TEXT | Local da etapa. |
| `categoria` | TEXT | Categoria disputada. |
| `nome` | TEXT | Nome do atleta. |
| `cbo` | INTEGER | Número CBO do atleta. |
| `clubeSigla` | TEXT | Sigla do clube na etapa. |
| `percursoId` | INTEGER | Percurso do atleta. |
| `distanciaM` | INTEGER | Distância do percurso do atleta, em metros. |
| `tempoSegundos` | INTEGER | Tempo oficial em segundos. |
| `ritmoSegundosPorKm` | INTEGER | Ritmo médio em segundos por quilômetro. |
| `ritmoTexto` | TEXT | O mesmo ritmo como `m'ss"`. |

### `vwRitmoTrecho`

Trechos que têm ritmo (sequência de postos conferida e distância do trecho conhecida), com os dados do atleta.

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ano` | INTEGER | Ano da edição. |
| `numeroEtapa` | INTEGER | Número da etapa. |
| `categoria` | TEXT | Categoria disputada. |
| `nome` | TEXT | Nome do atleta. |
| `cbo` | INTEGER | Número CBO do atleta. |
| `ordem` | INTEGER | Ordem do trecho. |
| `codigoPosto` | INTEGER | Posto em que o trecho termina; 999 é a chegada. |
| `distanciaM` | INTEGER | Distância do trecho em metros. |
| `tempoParcialSegundos` | INTEGER | Tempo do trecho em segundos. |
| `ritmoSegundosPorKm` | INTEGER | Ritmo do trecho em segundos por quilômetro. |
| `ritmoTexto` | TEXT | O mesmo ritmo como `m'ss"`. |

## Consultas de exemplo

Ritmo de uma categoria numa etapa, do mais rápido ao mais lento:

```sql
SELECT nome, clubeSigla, tempoSegundos, distanciaM, ritmoTexto
FROM vwRitmo
WHERE ano = 2026 AND numeroEtapa = 4 AND categoria = 'H Adulto E'
ORDER BY ritmoSegundosPorKm;
```

Evolução de um atleta (compare só linhas da mesma categoria ou do mesmo percurso):

```sql
SELECT ano, numeroEtapa, categoria, distanciaM, ritmoTexto
FROM vwRitmo
WHERE cbo = 18825
ORDER BY ano, numeroEtapa;
```

Ritmo médio por categoria numa etapa, com a quantidade de atletas:

```sql
SELECT categoria, COUNT(*) AS atletas, ROUND(AVG(ritmoSegundosPorKm)) AS mediaSegundosPorKm
FROM vwRitmo
WHERE ano = 2026 AND numeroEtapa = 1
GROUP BY categoria
ORDER BY categoria;
```

Trechos de um atleta numa etapa:

```sql
SELECT ordem, codigoPosto, distanciaM, tempoParcialSegundos, ritmoTexto
FROM vwRitmoTrecho
WHERE ano = 2026 AND numeroEtapa = 4 AND cbo = 18825
ORDER BY ordem;
```

Participações sem ritmo e o motivo:

```sql
SELECT motivoSemRitmo, COUNT(*) AS participacoes
FROM participacao
WHERE ano = 2026 AND ritmoSegundosPorKm IS NULL
GROUP BY motivoSemRitmo;
```
