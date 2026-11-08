---
description: Especificação do motor de cálculo de pontuação individual, descarte, média de voluntários, clubes e desempates (Arts. 31 a 35).
status: ativa
---

# Especificação: Motor de Cálculo do Campeonato

## O Quê
Motor determinístico em [`src/motorCalculo/`](../../../src/motorCalculo/) que recebe os resultados das etapas/percursos de uma edição (CCO ou CCOS) e a lista de voluntários/árbitros, calculando a classificação individual final por categoria e a classificação geral de clubes.

## Regras de Negócio (Base: Regulamento 2026/2027)
1. **Pontuação por Etapa/Percurso (Art. 31):**
   - 1º ao 26º colocados: `40, 37, 35, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11`.
   - 27º colocado em diante (que concluir o percurso): `10` pontos.
   - Atletas de percursos anulados e atletas não classificados (NC / DNF / DSQ / MP que partiram): `1` ponto pela participação.
   - Categorias Acompanhadas (`HN1`, `HN2`, `HN3`, `DN1`, `DN2`, `DN3`) e percursos Abertos: não pontuam (`0`).
2. **Troca de Categoria (Art. 32):**
   - Pontuação não é cumulativa entre categorias diferentes. Prevalece para classificação final a categoria de melhor resultado (ou a mais recente, em caso de empate).
3. **Descarte no CCO (Art. 34 e Art. 23, Parágrafo Único):**
   - Exclusivo do CCO quando houver **mais de 3 etapas efetivamente realizadas** (`etapas_realizadas > 3`).
   - Descarta-se obrigatoriamente 1 etapa (a de menor pontuação do atleta, incluindo `0` de ausência).
   - Se `etapas_realizadas <= 3`, não há descarte.
   - Etapa em que o atleta sofreu a penalidade do Art. 23, Parágrafo Único (não registrou chegada / não devolveu SI-Card/mapa ao desistir) é marcada como **não passível de descarte**.
4. **Pontuação de Voluntários e Árbitros (Art. 33):**
   - **No CCO (§ 1º):** exige participação em pelo menos `floor(etapas_realizadas / 2)` etapas. A média é calculada sobre as etapas em que o atleta se inscreveu (exceto a de voluntário), aplicando-se previamente o descarte do Art. 34.
   - **No CCOS (§ 2º):** média dos outros percursos do mesmo evento.
5. **Pontuação de Clubes (Art. 35):**
   - Soma dos pontos dos **3 atletas filiados à CBO melhores classificados em cada categoria**, por etapa/percurso.
   - Clubes não filiados à CBO/FECORI não entram na classificação oficial de clubes (ou são listados apenas a título informativo conforme regra histórica).
6. **Critérios de Desempate e Elegibilidade à Premiação (Arts. 34 § 2º, 35 Parágrafo Único e 39 § 1º):**
   - **Individual:** melhor resultado no último percurso → percurso anterior sucessivamente → maior idade.
   - **Clubes:** maior número de 1ºs lugares → 2ºs lugares → sucessivamente.
   - **Elegibilidade à Premiação Final (Art. 39 § 1º):** indicação se o atleta cumpriu o mínimo de metade das etapas/percursos realizados e filiação regular à CBO.
7. **Unificação de Cadastros (CBO Provisório para CBO Oficial):**
   - Quando um atleta participa de etapa inicial com código provisório no Helga (`>= 100000`) e regulariza sua filiação à CBO/clube nas etapas seguintes, o mapeamento registrado na seção `## Unificação de Cadastros` de `voluntariosCCO.md` consolida as inscrições sob o CBO oficial e o respectivo clube filiado.

## Critérios de Aceitação
- [x] Cobertura de 100% das regras acima com testes unitários automatizados em `tests/`.
- [x] Geração de relatórios detalhando memória de cálculo (notas por etapa, nota descartada, média de voluntário e top 3 por categoria/clube) em Markdown (`.md`), Excel (`.xlsx`) e PDF (`.pdf`).
- [x] Testes de integração com dados sintéticos cobrem a apuração completa (`apurarCampeonatoCCO`: colocação, descarte, média de voluntário e pontuação de clubes), o PDF parcial (ausência da logo e "NÃO OFICIAL" à direita) e a planilha Excel (`tests/test_apuracao_integracao.py`).
- [x] A numeração romana da edição é calculada a partir do ano (2026 = XX), sem tabela fixa.
- [x] Geração do PDF de Resultado Parcial dos Atletas (`resultadoParcialCCO.pdf`) sem a logo da edição (por ser não oficial) e com o texto "NÃO OFICIAL" alinhado à direita da folha, na linha do título; a logo oficial (`logoCCO.jpeg`) só aparece nos relatórios gerados com `--oficial`. O PDF traz destaque rosa (`#FFC7CE`) para atletas inscritos em mais de uma categoria (Art. 32), destaque em cinza e com o texto riscado nas pontuações de etapas descartadas (Art. 34), itens formatados em bullet points abaixo do cabeçalho OBSERVAÇÕES informando sobre voluntários, descarte da pontuação mais baixa (Art. 34) e canal para inconformidades, e linha totalizadora de inscrições por etapa. Os relatórios finais (`resultadoIndividualCCO.pdf`, `resultadoClubesCCO.pdf` e `resultadoClubesCCO.md`) só podem ser gerados após a conclusão da revisão do `resultadoParcialCCO.pdf` e autorização pela FECORI (`--oficial`).


