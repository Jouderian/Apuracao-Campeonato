---
description: Ingestão da planilha exportada do site de resultados do Helga (lista de partida e resultado) como fonte complementar, quando o banco da etapa se perdeu ou veio sem resultados.
status: ativa
---

# Especificação: Ingestão da Planilha do Site de Resultados do Helga

## O Quê
Módulo [`leitorHelgaWeb.py`](../../../src/extracaoAccess/leitorHelgaWeb.py) que lê a planilha `Dados/<ano>/entradas/exportadoSiteHelga.xlsx`, exportada à mão do site de resultados do Helga (HelgaO WebRes), e gera o JSON complementar `Dados/<ano>/extraidos/etapasHelgaWeb<ano>.json`, no mesmo esquema do `etapasHelga<ano>.json`. O CLI de apuração mescla os dois: as etapas do complemento **substituem** as de mesmo número do banco.

## Por Quê
Em 2025 o banco da 2ª etapa se perdeu e o da 3ª trazia as inscrições sem nenhum resultado. O site de resultados do Helga publica, por etapa, a lista de partida (todos os inscritos) e o resultado (quem largou). Juntas, as duas listas determinam o resultado de cada inscrito (concluiu, NC, OT ou NP), que é o que o motor precisa.

## Entrada (planilha)
Uma aba `listaPartidaEtapa<N>` e uma `resultadoEtapa<N>` por etapa.
- **Lista de partida:** blocos por clube (`<Clube> (<n>)`), com uma linha por inscrito: CBO, nome, código do Helga (`#id#`), horário de largada e categoria.
- **Resultado:** blocos por categoria (`<Categoria> (<n>) length <m>m ...`), com colocação (`1.`, `2.`... ou `NCL`, `OT`, `ACT`), CBO, nome, clube, tempo, min/km e diferença para o líder.
- O Excel lê os tempos `mm:ss` como `hh:mm`. O tempo de cada atleta é a leitura que bate com min/km × distância da categoria; sem uma única leitura compatível, a extração é recusada.

## Regras
1. **Categorias fora do CCO:** categorias com prefixo `Militar` não valem para o CCO e são ignoradas (na 3ª etapa de 2025, a Operação Militar correu junto; no banco elas constavam como `Aberto C/D/H/L`).
2. **Situação de cada inscrito** (lista de partida × resultado): colocação numérica = concluiu (`OK`, com tempo); `NCL` = não classificado (`NC`); `OT` = fora de tempo; `ACT` = acompanhado (`OK`, sem tempo, categorias que não pontuam); inscrito sem linha de resultado = não largou (`NP`).
3. **Recusa a extração** (lista de todos os problemas) quando: resultado de atleta ausente da lista de partida na mesma categoria; colocações fora de sequência; contagem de linhas diferente do `(n)` do cabeçalho; tempo fora de ordem, sem leitura única compatível com min/km ou divergente da diferença para o líder; clube da lista ausente da tabela de clubes do banco (a menos que o apurador declare o mesmo clube grafado de outro modo com `--alias-clube`, confirmado pelo cadastro dos atletas); etapa nova sem metadados.
4. **Avisa** (não recusa) quando dois classificados da mesma categoria têm o mesmo tempo: a ordem segue a colocação do site.
5. **Etapas com o banco disponível** (como a 3ª de 2025) mantêm no complemento o número, a data, o local e o `competitionId` do banco; etapas sem banco recebem os metadados informados no comando (`--etapa-nova`).
6. **Atletas novos** (CBO fora do cadastro do banco) entram em `perfisAtletas` com o clube da lista de partida.
7. **Congelamento:** o SHA-256 da planilha entra em `Dados/arquivosCongelados.sha256` (`<ano>/exportadoSiteHelga.xlsx`). Hash já registrado e diferente recusa a extração. A planilha é versionada no Git como memória de cálculo esportiva pública, e o JSON complementar traz o hash em `sha256Fonte`.

## Critérios de Aceitação
- [x] Leitura da lista de partida e do resultado com testes sintéticos (leitura de tempo `mm:ss` e `h:mm:ss`, status, NP, categorias militares, recusas).
- [x] Mesclagem do complemento ao JSON do banco, substituindo as etapas de mesmo número, com validação de estrutura e conferência de hash de cada arquivo.
- [x] `Dados/2025/extraidos/etapasHelgaWeb2025.json` gerado e validado; apuração de 2025 com as 4 etapas.
