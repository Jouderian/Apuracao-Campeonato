---
description: Especificação do motor de cálculo de pontuação individual, descarte, média de voluntários, clubes e desempates, parametrizado pelo regulamento de cada ano (2025: Arts. 34 a 42; 2026: Arts. 31 a 39).
status: ativa
---

# Especificação: Motor de Cálculo do Campeonato

## O Quê
Motor determinístico em [`src/motorCalculo/`](../../../src/motorCalculo/) que recebe os resultados das etapas/percursos de uma edição (CCO ou CCOS) e a lista de voluntários/árbitros, calculando a classificação individual final por categoria e a classificação geral de clubes.

## Princípio: o Regulamento do Ano Manda
Este repositório complementa o [Regulamentos-de-Orientacao](https://github.com/Jouderian/Regulamentos-de-Orientacao). Cada edição é apurada **pelo regulamento do seu próprio ano**, em `Documentos/<ano>/` daquele repositório. É proibido assumir que o regulamento mais recente vale para anos anteriores, ou que o anterior vale para os seguintes.

1. As regras de cada ano vivem em [`src/motorCalculo/regulamentos.py`](../../../src/motorCalculo/regulamentos.py) como um conjunto imutável (`RegrasRegulamento`) por par (ano, competição), com a citação dos artigos e do arquivo-fonte.
2. O motor e os relatórios **recebem** o conjunto de regras; nenhuma constante de regulamento fica fixa no código de cálculo ou de relatório.
3. Ano sem conjunto de regras registrado **não é apurado**: o comando recusa com erro (`RegulamentoNaoMapeadoError`), sem usar o ano vizinho como substituto. O `verificar-projeto.py` recusa `Dados/<ano>/extraidos/` de ano sem regras.
4. **Para registrar um ano novo:** ler o regulamento daquele ano, comparar com os já mapeados (tabela abaixo), registrar o conjunto de regras com os artigos, atualizar esta spec e criar testes. Interpretação de regra esportiva ambígua vai para ADR ([ADR-005](../../wiki/decisions/ADR-005-regulamento-por-ano-na-apuracao.md)).

### Diferenças entre os regulamentos mapeados (CCO)
| Tema | 2025 (XIX CCO) | 2026 (XX CCO) |
| :--- | :--- | :--- |
| Pontuação por etapa | Art. 34 (tabela de 40 a 11; 10 a partir do 27º; 1 ponto para anulado/não classificado) | Art. 31 (mesma tabela e valores) |
| Troca de categoria | Art. 35 | Art. 32 |
| Voluntários e árbitros | Art. 36: média das outras etapas, dividida por **todas** as outras etapas realizadas (0 nas sem inscrição e na outra etapa de apoio); a etapa de apoio conta no mínimo de metade das etapas (arredondada para cima) | Art. 33: média das etapas em que se inscreveu, após descarte; metade das etapas realizadas, arredondando para baixo; a etapa de apoio conta |
| Descarte | **Não há** (Art. 38: "sem descartes") | 1 etapa, se o campeonato tiver mais de 3 etapas realizadas (Art. 34) |
| Penalidade de não registrar chegada | Art. 20, Parágrafo Único (etapa não passível de descarte; sem efeito prático por não haver descarte) | Art. 23, Parágrafo Único |
| Clubes | Art. 37 e Art. 39: o texto diz 3 melhores filiados por categoria, por etapa; **o publicado soma os 3 melhores totais finais por categoria, só classifica clubes da FECORI e conta na coluna Atletas as linhas do clube no resultado individual; é esse o método aplicado** (ADR-007) | Art. 35: 3 melhores filiados por categoria, por etapa; clubes filiados à CBO; atletas distintos |
| Desempate individual | Art. 38, Parágrafo Único: mais 1ºs lugares, depois 2ºs e assim por diante; melhor resultado no último confronto direto; maior idade | Art. 34, § 2º: melhor resultado no último percurso, percursos anteriores sucessivamente; maior idade |
| Desempate de clubes | Art. 39, Parágrafo Único: mais 1ºs lugares, depois 2ºs | Art. 35, Parágrafo Único (idem) |
| Premiação final | Art. 42, § 1º | Art. 39, § 1º |

## Regras de Negócio
As regras abaixo descrevem o comportamento comum e, onde diferem, indicam o ano. Os artigos citados sem ano são os de 2026; a tabela acima traz os de 2025.

1. **Pontuação por Etapa/Percurso (2025: Art. 34; 2026: Art. 31):**
   - 1º ao 26º colocados: `40, 37, 35, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11`.
   - 27º colocado em diante (que concluir o percurso): `10` pontos.
   - Atletas de percursos anulados e atletas não classificados (NC / DNF / DSQ / MP que partiram): `1` ponto pela participação.
   - Categorias Acompanhadas (`HN1`, `HN2`, `HN3`, `DN1`, `DN2`, `DN3`) e percursos Abertos: não pontuam (`0`).
   - O texto de 2025 diz "os 31 primeiros colocados", mas lista 26 valores e dá 10 pontos a partir do 27º; vale a tabela de 26 valores (mesma de 2026).
2. **Troca de Categoria (2025: Art. 35; 2026: Art. 32):**
   - Pontuação não é cumulativa entre categorias diferentes. Prevalece para classificação final a categoria de melhor resultado (ou a mais recente, em caso de empate).
3. **Descarte (2026: Art. 34 e Art. 23, Parágrafo Único; 2025: inexistente):**
   - **2026:** exclusivo do CCO quando houver **mais de 3 etapas efetivamente realizadas** (`etapas_realizadas > 3`). Descarta-se obrigatoriamente 1 etapa (a de menor pontuação do atleta, incluindo `0` de ausência). Se `etapas_realizadas <= 3`, não há descarte. Etapa em que o atleta sofreu a penalidade do Art. 23, Parágrafo Único (não registrou chegada / não devolveu SI-Card/mapa ao desistir) é marcada como **não passível de descarte**.
   - **2025:** nunca há descarte; a classificação é o somatório de todas as etapas (Art. 38).
4. **Pontuação de Voluntários e Árbitros (2025: Art. 36; 2026: Art. 33):**
   - **No CCO:** o atleta precisa atingir o mínimo de etapas (`floor(etapas_realizadas / 2)` em 2026; ver ADR-005 para 2025). A média é calculada sobre as etapas em que o atleta se inscreveu (exceto a de voluntário), aplicando-se previamente o descarte **somente quando o regulamento do ano o prevê**.
   - **Mínimo:** nos dois anos a etapa de voluntário/árbitro conta como participação (2025 confirmado pelo resultado oficial publicado, ADR-005).
   - **Divisor da média:** 2026, as etapas em que o atleta se inscreveu (após o descarte); 2025, todas as outras etapas realizadas, com 0 ponto nas sem inscrição e na outra etapa de apoio.
   - **No CCOS (2026, § 2º):** média dos outros percursos do mesmo evento (ainda não implementado no motor).
5. **Pontuação de Clubes (2025: Arts. 37 e 39; 2026: Art. 35):**
   - **2026:** soma dos pontos dos **3 atletas filiados à CBO melhores classificados em cada categoria**, por etapa/percurso.
   - **2025:** soma, para cada clube e categoria, dos totais finais dos 3 atletas filiados com maior total (como no resultado publicado, ADR-007). A pontuação por etapa do clube é a soma das notas de cada etapa desses atletas.
   - Clubes não filiados não entram na classificação oficial de clubes: em 2025 (Art. 40) só os filiados à FECORI (o CODAC, da FOMS, fica de fora); em 2026 (Art. 35), os filiados à CBO.
6. **Critérios de Desempate e Elegibilidade à Premiação:**
   - **Individual 2026:** melhor resultado no último percurso → percurso anterior sucessivamente.
   - **Individual 2025:** maior número de 1ºs lugares → 2ºs lugares → sucessivamente; persistindo, melhor resultado no último confronto direto, aplicado quando **todos** os empatados disputaram a mesma etapa e foram classificados nela; sem essa condição, o empate fica sinalizado (ADR-005).
   - **Em ambos:** o critério de *maior idade* **não é aplicado**, pois o ano de nascimento não é extraído nem versionado ([ADR-003](../../wiki/decisions/ADR-003-sem-ano-de-nascimento-e-desempate-por-idade.md)). Persistindo o empate, a ficha recebe `empateNaoResolvido = True`, a ordem de apresentação segue o número CBO e o relatório avisa que o apurador deve decidir fora do repositório.
   - **Clubes (ambos):** maior número de 1ºs lugares → 2ºs lugares → sucessivamente.
   - **Elegibilidade à Premiação Final (2025: Art. 42, § 1º; 2026: Art. 39, § 1º):** indicação se o atleta cumpriu o mínimo de metade das etapas/percursos realizados e filiação regular à CBO.
7. **Unificação de Cadastros (CBO Provisório para CBO Oficial):**
   - Quando um atleta participa de etapa inicial com código provisório no Helga (`>= 100000`) e regulariza sua filiação à CBO/clube nas etapas seguintes, o mapeamento registrado na seção `## Unificação de Cadastros` de `voluntariosCCO.md` consolida as inscrições sob o CBO oficial e o respectivo clube filiado.
8. **Ajustes do Resultado Oficial Publicado (ADR-007):** a seção `Ajustes do Resultado Oficial Publicado` do `voluntariosCCO.md` lista (etapa, CBO, categoria, pontos publicados, motivo). O motor substitui a nota da etapa pelo valor publicado depois do cálculo (inclusive da média de voluntário) e antes do total, do descarte e da classificação; ajuste sem ficha correspondente recusa a apuração. A seção `Posições do Resultado Oficial Publicado` fixa a posição na categoria dos atletas cujo empate o publicado resolveu por critério que o repositório não aplica (idade, ADR-003) ou que ele colocou em posição diferente da calculada; o atleta com posição publicada deixa de ter empate pendente. O relatório Markdown marca com † as notas ajustadas e informa a quantidade de ajustes e posições; o PDF parcial informa o mesmo nas OBSERVAÇÕES. A coluna opcional `Destaque` (`média`) da seção de ajustes faz o PDF final pintar a nota ajustada de amarelo, como o publicado. A seção `Atletas Fora do Resultado Oficial Publicado` (categoria, CBO, motivo) omite do resultado as linhas que o publicado não tinha; o motor recusa omissão de atleta com pontos ou sem ficha correspondente.
9. **Etapas Realizadas:** o total de etapas realizadas é o número de etapas presentes no JSON extraído. Os relatórios mostram uma coluna por etapa presente (não há 4 colunas fixas), pois etapas canceladas ou ausentes do banco não entram na apuração. O comando avisa (sem interromper) quando uma etapa do calendário está ausente do banco ou quando uma etapa presente só tem inscrições NP/CC, porque o total de etapas realizadas decide descarte, mínimo de voluntários e elegibilidade à premiação (`diagnosticarEtapas`).

## Critérios de Aceitação
- [x] Cobertura de 100% das regras acima com testes unitários automatizados em `tests/`.
- [x] Geração de relatórios detalhando memória de cálculo (notas por etapa, nota descartada, média de voluntário e top 3 por categoria/clube) em Markdown (`.md`), Excel (`.xlsx`) e PDF (`.pdf`).
- [x] Testes de integração com dados sintéticos cobrem a apuração completa (`apurarCampeonatoCCO`: colocação, descarte, média de voluntário e pontuação de clubes), o PDF parcial (ausência da logo e "NÃO OFICIAL" à direita) e a planilha Excel (`tests/test_apuracao_integracao.py`).
- [x] O motor não recebe nem usa dados pessoais além do mínimo: o JSON extraído não contém `anoNascimento` e é recusado se contiver; o motor só roda com entrada validada (estrutura e hash `sha256Fonte` conferido no manifesto).
- [x] Empate que persistiria até o critério de idade é sinalizado (`empateNaoResolvido`) no motor, no Markdown e na saída do comando, sem decidir por dado pessoal.
- [x] A numeração romana da edição é calculada a partir do ano (2026 = XX), sem tabela fixa.
- [x] Geração do PDF de Resultado Parcial dos Atletas (`resultadoParcialCCO.pdf`) sem a logo da edição (por ser não oficial) e com o texto "NÃO OFICIAL" alinhado à direita da folha, na linha do título; a logo oficial (`logoCCO.jpeg`) só aparece nos relatórios gerados com `--oficial`. O PDF e a aba `resultadoParcial` da planilha Excel trazem destaque rosa (`#FFC7CE`) para atletas inscritos em mais de uma categoria (troca de categoria), destaque com fundo amarelo (`#FFFF00`) nas etapas em que o atleta atuou como voluntário ou árbitro com média atribuída, destaque em cinza e com o texto riscado nas pontuações de etapas descartadas (somente quando o regulamento do ano prevê descarte), itens formatados em bullet points com quebra dinâmica de linha para preenchimento harmônico abaixo do cabeçalho OBSERVAÇÕES informando sobre voluntários (com indicação do destaque em amarelo das médias), descarte da pontuação mais baixa (somente quando aplicado) e canal para inconformidades, e linha totalizadora de inscrições por etapa. Os artigos citados nos relatórios são os do regulamento do ano apurado. Os relatórios finais (`resultadoIndividualCCO.pdf`, `resultadoClubesCCO.pdf` e `resultadoClubesCCO.md`) só podem ser gerados após a conclusão da revisão do `resultadoParcialCCO.pdf` e autorização pela FECORI (`--oficial`). O PDF individual final (`gerarPdfResultadoIndividualFinal`) segue o layout publicado pela FECORI: A4 paisagem, título "Resultado Individual do <edição> Campeonato Cearense de Orientação" (logo da edição à esquerda, se existir `Dados/<ano>/logoCCO.*`), uma linha por atleta e categoria, categorias na ordem da FECORI e inteiras na página, pontos por etapa com destaque (amarelo para média de voluntário/árbitro, laranja claro com texto vermelho para não classificado com 1 ponto), coluna Premiação (troféu para campeão, ouro para campeão de categoria Novato, prata, bronze, ou o rótulo do artigo da participação mínima para quem está entre os 3 primeiros sem direito à premiação), total zero como "-", e, na última página, a linha de totais, o quadro de premiação e a legenda com os artigos do regulamento do ano. Não há aviso de "NÃO OFICIAL", nem observações, nem destaque de troca de categoria.
- [x] **PDF de clubes final:** `gerarPdfResultadoClubes` segue o layout publicado pela FECORI (A4 paisagem; cinco colunas: Class., Brasão, Clube, Atletas, Total Pontos; logo da edição, logo da FECORI e brasão de cada clube, quando os arquivos existem em `Dados/`).
- [x] **Resultado publicado:** os ajustes oficiais são aplicados, validados (ficha inexistente recusa) e sinalizados nos relatórios; a soma de clubes de 2025 segue o publicado; a apuração de 2025 reproduz, atleta por atleta e clube a clube, o resultado publicado.
- [x] **Regulamento por ano:** o comando recusa ano/competição sem regras registradas; o conjunto de regras de 2025 e o de 2026 têm testes próprios (descarte, média de voluntário, mínimo de etapas, desempate); os relatórios citam os artigos do ano apurado e mostram só as etapas realizadas.
- [x] O `verificar-projeto.py` recusa `Dados/<ano>/extraidos/` de ano sem regras registradas em `regulamentos.py`.
