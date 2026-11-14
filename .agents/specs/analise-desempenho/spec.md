---
description: Extração dos percursos e das parciais do Helga e consultas de desempenho dos atletas (ritmo médio, evolução, comparativos), fora da apuração do campeonato.
status: ativa
---

# Especificação: Análise de Desempenho dos Atletas

## O Quê
Aproveitar os dados do `HelgaDat.mdb` que a apuração não usa (distância e subida dos percursos, postos e parciais de cada atleta) para responder consultas esportivas, como o ritmo médio por atleta, etapa, categoria e ano. Três camadas, entregues em ordem:

- **Camada A, percursos e ritmo:** extrai os percursos e calcula o ritmo médio de cada atleta em cada etapa.
- **Camada B, parciais:** extrai a passagem de cada atleta em cada posto e calcula o ritmo por trecho.
- **Camada C, consultas:** módulo que cruza os JSON de vários anos e gera relatórios e, opcionalmente, uma base consultável.

## Por Quê
A extração atual ([`extrairHelga.py`](../../../src/extracaoAccess/extrairHelga.py)) lê só `Competition`, `Club`, `Person` e `Course`, o necessário à pontuação. O banco de 2026 também traz, sem uso:

| Tabela | Conteúdo | Preenchimento em 2026 (etapas 35 a 38) |
| :--- | :--- | :--- |
| `Parcours` | `Length` e `Climbing` de cada percurso | `Length` em 71 de 71 percursos; `Climbing` em 61 de 71 |
| `Cat_Parc` | categoria → percurso, `TimeLimit` | categoria → percurso em todas as etapas; `TimeLimit` vazio |
| `Course` | `Parcours_FK`, `StartTime`, `FinishTime`, `Penalty`, `ErrorAtControl` | `Parcours_FK` e `StartTime` em 100% das inscrições; `FinishTime` só em quem terminou |
| `Controls` | postos de cada percurso, `Order_Number`, `Distance` entre postos | 1.114 linhas no banco inteiro |
| `EmitData`, `EmitData_Details` | passagem de cada atleta por posto (`split`, `control`) | 10.537 passagens no banco inteiro |

Os números por etapa de `Controls` e das passagens, e a unidade de `Length`, ainda não foram conferidos (ver *Pontos em Aberto*).

## Princípios
1. **Fora da apuração:** nada desta spec altera pontuação, descarte, desempate ou clubes. O ritmo é informativo e nunca entra no motor de cálculo ([`scoring-engine`](../scoring-engine/spec.md)).
2. **Arquivos separados:** os dados novos vão em arquivos próprios, sem mudar o esquema de `etapasHelga<ano>.json`, para não afetar a apuração. O vínculo é por `competitionId` e `runnerPk` (ou `cbo`).
3. **Só os JSON como fonte das consultas:** a Camada C nunca abre o `.mdb`. A extração é o único passo que lê o banco.
4. **Dado esportivo vem dos dados:** distância, subida e tempos nunca são estimados. Dado ausente fica ausente e é listado, não preenchido.
5. **LGPD:** nenhum campo pessoal novo. Nome e CBO já constam dos JSON; ano de nascimento continua proibido ([ADR-003](../../wiki/decisions/ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)), logo não há recorte por idade, apenas por categoria.
6. **Congelamento:** a extração só roda sobre arquivo cujo SHA-256 esteja em [`Dados/arquivosCongelados.sha256`](../../../Dados/arquivosCongelados.sha256); hash divergente recusa.

## Camada A: Percursos e Ritmo

### Saída
`Dados/<ano>/extraidos/percursosHelga<ano>.json`, com `fonte`, `sha256Fonte` e:
- `percursos`: `percursoId`, `competitionId`, `numero`, `nome`, `distanciaM`, `subidaM` (ambos nulos quando o Helga traz zero, que ali significa campo não informado).
- `categoriaPercurso`: `competitionId`, `categoriaId`, `percursoId`.
- `participacoes`: `competitionId`, `runnerPk`, `percursoId` (de `Course.Parcours_FK`), `horaLargada`, `horaChegada`.

### Regras
1. O percurso do atleta é `Course.Parcours_FK`, e não o da categoria, pois os dois podem divergir.
2. **Ritmo médio** = `tempoSegundos` ÷ (`distanciaM` ÷ 1000), em min/km, só para `statusCodigo = 0` com tempo e distância. O ritmo se arredonda ao segundo com a metade para cima, em aritmética inteira (não usar o arredondamento padrão do Python, que leva a metade ao par). Em empate exato de meio segundo o site do HelgaO às vezes diverge em 1 s (ver Ponto em Aberto 1); fora dos empates coincide. Os demais ficam sem ritmo, com o motivo registrado.
3. O ritmo vem sempre rotulado como informativo e traz a distância usada.
4. **Comparação:** ritmos só se comparam dentro da mesma categoria ou do mesmo percurso (decisão do apurador, 2026-11-13). Não há ritmo ajustado entre percursos diferentes.
5. **Fonte da distância:** `Parcours.Length` do banco. As etapas sem resultado no banco (2025, etapas 2 e 3, apuradas pela planilha do site, [ADR-006](../../wiki/decisions/ADR-006-planilha-do-site-helga-como-fonte-complementar.md)) ficam fora da Camada A (decisão do apurador, 2026-11-14): sem os dados do percurso de cada atleta não há ritmo. A planilha traz só a distância por categoria e o min/km, e poderia servir em nível de categoria se a decisão mudar.
6. **Recusa a extração** (listando todos os problemas) quando: `Length` ausente ou zero em percurso usado por quem concluiu (`statusCodigo` 0); `Parcours_FK` aponta para percurso inexistente; unidade de `Length` incompatível com a planilha do site na etapa em que as duas fontes existem.

## Camada B: Parciais por Posto

### Saída
`Dados/<ano>/extraidos/parciaisHelga<ano>.json`, com `fonte`, `sha256Fonte` e:
- `percursos`: `percursoId` e a lista ordenada de `postos` (`ordem`, `codigoPosto`, `distanciaM` do trecho que termina no posto, de `Controls.Distance`).
- `participacoes`: de quem concluiu (`statusCodigo` 0) e teve as parciais aceitas: `competitionId`, `runnerPk`, `percursoId`, `tempoOficialSegundos`, `passagens` (`ordem`, `codigoPosto`, `tempoParcialSegundos`) e `postosConferem` (a sequência lida é igual à do percurso).
- `ocorrencias`: `competitionId`, `runnerPk` e `motivo` de cada concluinte sem parciais aceitas ou com sequência divergente.

### Regras
1. **Vínculo:** as passagens vêm de `EmitData_Details` (ligada a `EmitData` por `EmitData_pk` = `id`), e `EmitData` liga-se a `Course` por `Competition_FK` = `Competition_PK` e `BadgeNumber` = `Course.EmitBadge` (`RealBadgeNumber` vem vazio). O número do chip não vai para o JSON.
2. **Leituras repetidas (decidido em 2026-11-13):** o mesmo chip pode ter várias linhas em `EmitData`. Vale apenas a **última leitura** (maior `id`).
3. **Conferência da soma:** a soma das parciais, incluindo o posto de chegada (`control` 999), deve igualar `Course.CourseTime` com tolerância de 1 s. Quando não igualar (ou não houver chip ou passagens), a participação fica sem parciais e vai para `ocorrencias` com os dois valores, sem trocar de leitura nem corrigir.
4. **Sequência dos postos:** igual à de `Controls` (por `Order_Number`), `postosConferem` é verdadeiro. Diferente (posto pulado, repetido ou fora de ordem), as parciais são mantidas com `postosConferem` falso e a participação entra em `ocorrencias`, sem correção; nesse caso não há ritmo por trecho, pois a distância do trecho só vale na sequência do percurso.
5. **Distância do trecho:** `Controls.Distance` (o primeiro trecho parte da largada; o último, posto 999, é o da chegada). Em 8 percursos de 2026, a soma dos trechos fica entre 0,3% e 1,7% abaixo de `Parcours.Length`; a natureza dessa distância (por exemplo, em linha reta) não foi verificada. Por isso o ritmo por trecho não reproduz exatamente o ritmo do percurso e é informativo, com a mesma regra de comparação da Camada A (mesma categoria ou mesmo percurso).
6. **Ritmo por trecho:** `calcularRitmoSegundosPorKm` da Camada A sobre a parcial e a distância do trecho; parcial zero ou negativa fica sem ritmo.
7. **Escopo:** só quem concluiu. As etapas sem resultado no banco (2025, etapas 2 e 3) ficam fora, como na Camada A.

## Camada C: Consultas

### Módulo
`src/analises/`, lendo os JSON de `Dados/<ano>/extraidos/` (os já existentes mais os das Camadas A e B).

### Consultas previstas
- Ritmo médio de um atleta por etapa, por ano e acumulado, dentro da mesma categoria ou do mesmo percurso.
- Evolução de um atleta ao longo das etapas e dos anos, pela chave `cbo` (respeitando as unificações de CBO do `voluntariosCCO.md`).
- Ritmo de uma categoria numa etapa: mediana e dispersão.
- Com a Camada B: posto de maior perda de tempo de um atleta contra o líder da categoria.

### Saída
Relatórios em `Dados/<ano>/resultados/` (`.md` e `.xlsx`, como os demais). Para consultas livres entre anos, uma base SQLite gerada dos JSON por `src/analises/gerarBase.py` e **ignorada pelo Git**, pois é derivada e reconstruível ([ADR-009](../../wiki/decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md)). O acesso é por `src/analises/consultar.py`, que abre a base só para leitura (`mode=ro`), aceita apenas `SELECT` e limita as linhas devolvidas. Um dicionário de dados em Markdown, em `.agents/wiki/`, descreve tabelas, colunas, unidades e regras para a IA consultar.

## Fora de Escopo
- Qualquer efeito sobre pontuação, descarte, desempate ou resultado de clubes.
- Dados pessoais além dos já existentes nos JSON; recortes por idade; contato, endereço, documento.
- Estimar distância, subida ou tempo ausentes.
- Ritmo ajustado pela subida para comparar percursos diferentes.
- Publicar análise nominal se a FECORI vier a regrar o assunto de modo restritivo (hoje não há regramento; ver *Pontos em Aberto*).

## Pontos em Aberto
Cada item precisa de decisão do apurador antes da implementação. Os que alteram arquitetura ou interpretação viram ADR.

1. **Unidade de `Parcours.Length` (pendente):** conferir no site do HelgaO os casos de 2026 abaixo, que trazem o ritmo calculado a partir de `Length`. Se o cabeçalho do site disser `length <m> m` com o mesmo valor e o min/km bater, a unidade (metros) está confirmada. **Resultado da conferência (2026-11-13):** quatro casos bateram e José Ronaldo de Brito Filho (etapa 2) divergiu em 1 s (site 15'52", calculado 15'51"), por um empate exato de meio segundo (3806 s ÷ 4 km = 951,5 s/km); a Camada A arredonda a metade para cima, o que acerta este caso. **Conferência no site (2026-11-14):** seis casos de 2025 das etapas 1 e 4 (sem empate exato), conferidos pelo apurador, bateram. **Conferência de 2025 (2026-11-14), contra a planilha do site:** o `length` do cabeçalho é igual ao `Length` do banco nas 39 categorias da etapa 3; o ritmo calculado coincide com o min/km da planilha em 252 de 258 linhas das etapas 2 e 3. As 6 divergências são de 1 s e todas em empates exatos de meio segundo: das 8 linhas com empate exato, o site desce em 6 e sobe em 2, sem regra que a data reproduza (nenhum arredondamento simples fecha todas). Causa provável, não verificada: o Helga calcula com o tempo em milissegundos, que o banco não traz (`CourseTime_ms` vem zerado em 2026) e a planilha também não. Fora dos empates, 250 de 250 linhas coincidem. A comparação com uma etapa de 2025 que tem banco e planilha continua válida como segunda conferência.

   | Etapa | Categoria | `Length` | 1º colocado | Tempo | Ritmo calculado |
   | :---: | :--- | ---: | :--- | :--- | :--- |
   | 1 | H Adulto E | 6100 m | Antonio David Tomás Da Silva (COCAP) | 00:59:48 | 9'48"/km |
   | 2 | H Adulto E | 4000 m | José Ronaldo de Brito Filho (COMaNE) | 01:03:26 | 15'51"/km |
   | 2 | D Adulto N | 1500 m | Antonia Giovana Gonçalves Ferreira (CORR) | 00:23:01 | 15'21"/km |
   | 3 | D Adulto E | 5900 m | Luana Kist Alves (COFORT) | 01:29:13 | 15'07"/km |
   | 4 | H Adulto E | 5700 m | Lamarck Augusto Gadelha Reges (TRILHA NORTE) | 00:47:49 | 8'23"/km |

   As etapas 2 a 4 também discriminam percursos com subida zero ou muito alta (`Climbing`), úteis para olhar o efeito do terreno no ritmo.
2. **Cobertura das parciais (medida em 2026-11-14):** com a última leitura do chip e a soma das parciais igual ao tempo oficial (tolerância de 1 s), 419 dos 448 concluintes de 2026 (93,5%) e 210 dos 230 de 2025 (91,3%) têm parciais completas e sequência de postos igual à do percurso. Os demais:

   | | 2026 | 2025 |
   | :--- | ---: | ---: |
   | Parciais e sequência conferem | 419 | 210 |
   | Soma fecha, mas a sequência de postos difere do percurso (posto pulado ou repetido) | 14 | 13 |
   | Sequência confere, mas a soma difere de 2 a 10 s do tempo oficial | 4 | 1 |
   | Soma difere muito do tempo oficial (sequência confere) | 9 | 5 |
   | Soma difere muito e a sequência difere | 2 | 1 |

   Nos casos de soma muito diferente, a primeira parcial costuma vir desproporcional (em dois casos inspecionados, 03:15:33 e, numa releitura, 11:59:31); a causa não foi verificada. Todos os postos de 2026 têm distância (`Controls.Distance`).
3. **Comparação de ritmos (decidido em 2026-11-13):** só dentro da mesma categoria ou do mesmo percurso. Sem ritmo ajustado pela subida.
4. **Divulgação (decidido em 2026-11-13):** a FECORI não tem regramento para este tipo de análise. Enquanto não houver, as saídas não têm restrição formal de divulgação, mas o assunto volta a esta spec se a FECORI regrar.
5. **Base consultável (decidido em 2026-11-13, [ADR-009](../../wiki/decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md)):** JSON oficial, SQLite gerado dos JSON e consultado por `consultar.py` (somente leitura), com dicionário de dados em Markdown. Sem dependência nova; DuckDB, pandas, servidor MCP e site de página única ficam para decisão futura.
6. **Anos anteriores (decidido em 2026-11-13):** só depois de estabilizar 2025 e 2026. Reextrair anos antigos depende de haver os arquivos originais e de congelá-los.

## Critérios de Aceitação
- [x] Pontos em Aberto 1 (conferência no site do HelgaO) e 5 (base consultável) respondidos e registrados nesta spec.
- [x] Camada A para 2026: `percursosHelga2026.json` gerado e validado (71 percursos, 166 vínculos categoria-percurso, 563 participações); ritmo de 448 participações calculado e conferido contra o min/km do site em cinco casos (`python src/analises/ritmoAtletas.py --ano 2026`).
- [x] Camada A para 2025: `percursosHelga2025.json` gerado (etapas 1 e 4, 230 participações com ritmo) e seis casos conferidos no site pelo apurador; as etapas 2 e 3 ficam fora (Camada A, regra 5).
- [x] Testes sintéticos: ritmo (inclusive a metade do segundo), recusas (sem percurso, percurso inexistente, sem distância) e vínculo do percurso do atleta, e não da categoria (`tests/test_ritmo.py`).
- [x] Camada B para 2025 e 2026: `parciaisHelga<ano>.json` gerado e validado (2026: 433 participações com parciais e 29 ocorrências; 2025: 223 e 20) e ritmo por trecho calculado por `python src/analises/parciaisAtleta.py --ano <ano> --etapa <N> --cbo <CBO>` (`tests/test_parciais.py`). Parciais conferidas no site do HelgaO pelo apurador (2026-11-14): os tempos de cada trecho de Lamarck Augusto Gadelha Reges na etapa 4 de 2026 batem; a distância por trecho não foi conferida no site.
- [x] Camada C: `gerarBase.py`, `consultar.py` (somente leitura, só `SELECT`, com limite de linhas e interrupção de consulta longa), [dicionário de dados](../../wiki/dicionario-dados-analise.md) e `.gitignore`, com testes (`tests/test_base_analise.py`, que também exige o dicionário cobrindo todas as colunas da base).
- [x] Seção de pastas de `Dados/` em `rules.md` com a pasta `Dados/analise/` (autorizado pelo apurador em 2026-11-14).
- [ ] `schema-access.md` atualizado com as tabelas novas e `wiki/index.md` com os ADRs gerados.
