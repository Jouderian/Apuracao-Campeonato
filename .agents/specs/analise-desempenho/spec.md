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
- `percursos`: `percursoId`, `competitionId`, `numero`, `nome`, `distanciaM`, `subidaM` (ou nulo) e, se a Camada B existir, a lista ordenada de postos.
- `categoriaPercurso`: `competitionId`, `categoriaId`, `percursoId`.
- `participacoes`: `competitionId`, `runnerPk`, `percursoId` (de `Course.Parcours_FK`), `horaLargada`, `horaChegada`.

### Regras
1. O percurso do atleta é `Course.Parcours_FK`, e não o da categoria, pois os dois podem divergir.
2. **Ritmo médio** = `tempoSegundos` ÷ (`distanciaM` ÷ 1000), em min/km, só para `statusCodigo = 0` com tempo e distância. O ritmo se arredonda ao segundo com metade para cima, como o site do HelgaO (não usar o arredondamento padrão do Python, que leva a metade ao par). Os demais ficam sem ritmo, com o motivo registrado.
3. O ritmo vem sempre rotulado como informativo e traz a distância usada.
4. **Comparação:** ritmos só se comparam dentro da mesma categoria ou do mesmo percurso (decisão do apurador, 2026-11-13). Não há ritmo ajustado entre percursos diferentes.
5. **Fonte da distância:** `Parcours.Length` do banco. Em etapas sem banco (2025, [ADR-006](../../wiki/decisions/ADR-006-planilha-do-site-helga-como-fonte-complementar.md)), o `length <m> m` do cabeçalho da planilha do site. Cada percurso registra de qual fonte veio a distância.
6. **Recusa a extração** (listando todos os problemas) quando: `Length` ausente ou zero em percurso usado por inscrição com resultado; `Parcours_FK` aponta para percurso inexistente; unidade de `Length` incompatível com a planilha do site na etapa em que as duas fontes existem.

## Camada B: Parciais por Posto

### Saída
`Dados/<ano>/extraidos/parciaisHelga<ano>.json`, com `fonte`, `sha256Fonte` e, por participação, a lista ordenada de passagens (`ordem`, `codigoPosto`, `tempoParcialSegundos`).

### Regras
1. As passagens vêm de `EmitData_Details` (ligada a `EmitData` por `EmitData_pk` = `id`), e `EmitData` liga-se a `Course` por `Competition_FK` = `Competition_PK` e `BadgeNumber` = `Course.EmitBadge` (`RealBadgeNumber` vem vazio). Se o vínculo não for unívoco para uma participação, ela vai para a lista de recusas, e não se escolhe por aproximação.
1. **Leituras repetidas (decidido em 2026-11-13):** o mesmo chip pode ter várias linhas em `EmitData`. Vale apenas a **última leitura** (maior `id`). Como conferência, a soma das parciais, incluindo o posto de chegada (`control` 999), deve igualar `Course.CourseTime`; quando não igualar, a participação fica sem parciais e vai para a lista de ocorrências, sem trocar de leitura nem corrigir.
2. A distância de cada trecho vem de `Controls.Distance`. Sem ela, o ritmo por trecho não se calcula e o trecho fica só com o tempo.
3. Posto fora da ordem do percurso, ou passagem repetida, é registrado como ocorrência da participação, sem correção.
4. Participações sem passagens (etapas de 2025 recuperadas pela planilha do site) ficam sem parciais; a ausência é explícita.

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

1. **Unidade de `Parcours.Length` (pendente):** conferir no site do HelgaO os casos de 2026 abaixo, que trazem o ritmo calculado a partir de `Length`. Se o cabeçalho do site disser `length <m> m` com o mesmo valor e o min/km bater, a unidade (metros) está confirmada. **Resultado da conferência (2026-11-13):** quatro casos bateram e José Ronaldo de Brito Filho (etapa 2) divergiu em 1 s (site 15'52", calculado 15'51"). Causa: 3806 s ÷ 4 km = 951,5 s/km exatos, e o site arredonda a metade para cima; a divergência foi só de arredondamento, que a Camada A passa a seguir. A comparação com uma etapa de 2025 que tem banco e planilha continua válida como segunda conferência.

   | Etapa | Categoria | `Length` | 1º colocado | Tempo | Ritmo calculado |
   | :---: | :--- | ---: | :--- | :--- | :--- |
   | 1 | H Adulto E | 6100 m | Antonio David Tomás Da Silva (COCAP) | 00:59:48 | 9'48"/km |
   | 2 | H Adulto E | 4000 m | José Ronaldo de Brito Filho (COMaNE) | 01:03:26 | 15'51"/km |
   | 2 | D Adulto N | 1500 m | Antonia Giovana Gonçalves Ferreira (CORR) | 00:23:01 | 15'21"/km |
   | 3 | D Adulto E | 5900 m | Luana Kist Alves (COFORT) | 01:29:13 | 15'07"/km |
   | 4 | H Adulto E | 5700 m | Lamarck Augusto Gadelha Reges (TRILHA NORTE) | 00:47:49 | 8'23"/km |

   As etapas 2 a 4 também discriminam percursos com subida zero ou muito alta (`Climbing`), úteis para olhar o efeito do terreno no ritmo.
2. **Cobertura das parciais (respondido para 2026):** todos os concluintes têm chip e passagens: 120 (etapa 1), 112 (etapa 2), 121 (etapa 3) e 95 (etapa 4), 448 no total. Todos os postos têm `Distance` (316, 222, 340 e 236). O chip tem várias leituras por atleta (na etapa 1, 308 linhas em `EmitData` para 133 chips distintos), regra tratada na Camada B. Com a regra da última leitura, a soma das parciais fecha o `CourseTime` (tolerância de 1 s) em 433 dos 448 concluintes (114, 106, 119 e 94 por etapa); 15 não fecham (6, 6, 2 e 1), alguns com soma muito maior que o tempo oficial, possivelmente chip usado por mais de um atleta (não verificado), e outros com 2 a 7 s de diferença. Nenhuma outra leitura do mesmo chip fecha esses 15. Esses casos ficam sem parciais e listados. Falta medir o mesmo para 2025.
3. **Comparação de ritmos (decidido em 2026-11-13):** só dentro da mesma categoria ou do mesmo percurso. Sem ritmo ajustado pela subida.
4. **Divulgação (decidido em 2026-11-13):** a FECORI não tem regramento para este tipo de análise. Enquanto não houver, as saídas não têm restrição formal de divulgação, mas o assunto volta a esta spec se a FECORI regrar.
5. **Base consultável (decidido em 2026-11-13, [ADR-009](../../wiki/decisions/ADR-009-base-sqlite-gerada-para-analise-de-desempenho.md)):** JSON oficial, SQLite gerado dos JSON e consultado por `consultar.py` (somente leitura), com dicionário de dados em Markdown. Sem dependência nova; DuckDB, pandas, servidor MCP e site de página única ficam para decisão futura.
6. **Anos anteriores (decidido em 2026-11-13):** só depois de estabilizar 2025 e 2026. Reextrair anos antigos depende de haver os arquivos originais e de congelá-los.

## Critérios de Aceitação
- [x] Pontos em Aberto 1 (conferência no site do HelgaO) e 5 (base consultável) respondidos e registrados nesta spec.
- [ ] Camada A: `percursosHelga2026.json` gerado e validado; ritmo médio de 2026 calculado e conferido à mão em ao menos uma categoria contra o min/km publicado pelo site.
- [ ] Camada A para 2025, com a distância da planilha do site nas etapas sem banco.
- [ ] Testes sintéticos: ritmo, recusas (distância ausente, percurso inexistente) e vínculo percurso do atleta × categoria.
- [ ] Camada B, com a cobertura de 2025 medida antes de implementar.
- [ ] Camada C: `gerarBase.py`, `consultar.py` (somente leitura, só `SELECT`, com limite de linhas) e dicionário de dados, com testes; ajuste do `.gitignore` e da seção de pastas de `Dados/` em `rules.md` com autorização expressa.
- [ ] `schema-access.md` atualizado com as tabelas novas e `wiki/index.md` com os ADRs gerados.
